#!/usr/bin/env python3
"""
M324 RefCard05 (Tim Held) - roll out one ECS Fargate service and verify the result.

    python3 deploy/ecs-deploy.py <backend|frontend> <image-uri> <version>

1. Reads the infrastructure values from the CloudFormation stack outputs (no account IDs,
   ARNs or endpoints are hard-coded in the repository).
2. Renders and registers a new task definition revision with the given image
   (health check, CPU/memory limits, logging, secrets).
3. Creates the service on the first run, otherwise updates it -> ECS starts new tasks
   (rolling update, deployment circuit breaker with automatic rollback).
4. Waits until the rollout is COMPLETED (or fails with the ECS events and stop reasons).
5. Verifies the deployed version through the public load balancer.
6. Writes a summary table to the GitHub Actions job summary.

Works the same in the Learner Lab and in a normal AWS account (task role from the stack outputs).
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROLLOUT_TIMEOUT_S = 20 * 60
VERIFY_TIMEOUT_S = 5 * 60

SERVICES = {
    # Resource limits: Fargate task size + JVM heap as a percentage of the container memory.
    'backend': {'port': 8080, 'cpu': '512', 'memory': '1024', 'health': '/actuator/health/readiness',
                'start_period': 120, 'desired': 1, 'target': 'BackendTarget', 'task_role': 'BackendTaskRoleArn'},
    'frontend': {'port': 80, 'cpu': '256', 'memory': '512', 'health': '/health',
                 'start_period': 15, 'desired': 1, 'target': 'FrontendTarget', 'task_role': 'FrontendTaskRoleArn'},
}


def log(msg):
    print(msg, flush=True)


def fail(msg):
    # GitHub Actions annotation -> shown prominently in the run summary.
    print(f'::error title=ECS deployment failed::{msg}', flush=True)
    raise SystemExit(1)


def aws(*args):
    region = os.environ.get('AWS_REGION', 'us-east-1')
    result = subprocess.run(['aws', *args, '--region', region, '--output', 'json'], capture_output=True, text=True)
    if result.returncode != 0:
        err = result.stderr.strip()
        if 'ExpiredToken' in err or 'InvalidClientTokenId' in err or 'UnrecognizedClient' in err:
            fail('AWS credentials rejected - the Learner Lab session has probably ended. '
                 'Start the lab and update the GitHub secrets AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / '
                 'AWS_SESSION_TOKEN (see docs/REFCARD05.md, "Secrets erneuern").')
        fail(f'aws {" ".join(args[:2])} failed: {err}')
    return json.loads(result.stdout) if result.stdout.strip() else {}


def stack_outputs(stack):
    stacks = aws('cloudformation', 'describe-stacks', '--stack-name', stack)['Stacks']
    return {o['OutputKey']: o['OutputValue'] for o in stacks[0].get('Outputs', [])}


def container_definition(service, image, version, out, region):
    cfg = SERVICES[service]
    name = f'biztrips-{service}'
    container = {
        'name': name,
        'image': image,
        'essential': True,
        'portMappings': [{'containerPort': cfg['port'], 'protocol': 'tcp'}],
        'stopTimeout': 30,
        'ulimits': [{'name': 'nofile', 'softLimit': 65536, 'hardLimit': 65536}],
        'logConfiguration': {'logDriver': 'awslogs', 'options': {
            'awslogs-group': out['LogGroup'], 'awslogs-region': region,
            'awslogs-stream-prefix': service, 'mode': 'non-blocking', 'max-buffer-size': '4m'}},
        'healthCheck': {
            'command': ['CMD-SHELL', f'wget -q -O /dev/null http://127.0.0.1:{cfg["port"]}{cfg["health"]} || exit 1'],
            'interval': 15, 'timeout': 5, 'retries': 3, 'startPeriod': cfg['start_period']},
        'dockerLabels': {'ch.bbw.m324.refcard': '05', 'ch.bbw.m324.version': version},
    }
    if service == 'backend':
        container['environment'] = [
            {'name': 'SPRING_PROFILES_ACTIVE', 'value': 'aws'},
            {'name': 'DB_HOST', 'value': out['DBEndpoint']},
            {'name': 'DB_PORT', 'value': out['DBPort']},
            {'name': 'DB_NAME', 'value': out['DBName']},
            {'name': 'APP_STORAGE_S3_BUCKET', 'value': out['PhotoBucket']},
            {'name': 'APP_STORAGE_S3_PREFIX', 'value': out['PhotoPrefix']},
            {'name': 'AWS_REGION', 'value': region},
        ]
        # Injected by the ECS agent from AWS Secrets Manager - never visible in the task definition.
        container['secrets'] = [
            {'name': 'DB_USER', 'valueFrom': out['DBSecretArn'] + ':username::'},
            {'name': 'DB_PASSWORD', 'valueFrom': out['DBSecretArn'] + ':password::'},
        ]
    else:
        container['environment'] = [{'name': 'BACKEND_ORIGIN', 'value': out['Endpoint']}]
    return container


def register_task_definition(service, image, version, out, region):
    cfg = SERVICES[service]
    task = {
        'family': f'bbw-m324-refcard05-{service}',
        'networkMode': 'awsvpc',
        'requiresCompatibilities': ['FARGATE'],
        'cpu': cfg['cpu'],
        'memory': cfg['memory'],
        'executionRoleArn': out['ExecutionRoleArn'],
        'taskRoleArn': out[cfg['task_role']],
        'runtimePlatform': {'cpuArchitecture': 'X86_64', 'operatingSystemFamily': 'LINUX'},
        'containerDefinitions': [container_definition(service, image, version, out, region)],
        'tags': [{'key': 'Project', 'value': 'M324-RefCard05'}, {'key': 'Version', 'value': version}],
    }
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(task, f, indent=2)
    log(f'::group::Task definition {task["family"]}\n{json.dumps(task, indent=2)}\n::endgroup::')
    return aws('ecs', 'register-task-definition', '--cli-input-json', f'file://{f.name}')['taskDefinition']['taskDefinitionArn']


def create_or_update_service(service, task_arn, out):
    cfg = SERVICES[service]
    cluster, name = out['ClusterName'], f'biztrips-{service}'
    existing = aws('ecs', 'describe-services', '--cluster', cluster, '--services', name)['services']
    if existing and existing[0]['status'] == 'ACTIVE':
        log(f'Updating service {name} -> {task_arn}')
        aws('ecs', 'update-service', '--cluster', cluster, '--service', name, '--task-definition', task_arn,
            '--force-new-deployment')
        return
    log(f'Creating service {name} (first deployment)')
    config = {
        'cluster': cluster, 'serviceName': name, 'taskDefinition': task_arn, 'desiredCount': cfg['desired'],
        'launchType': 'FARGATE', 'healthCheckGracePeriodSeconds': 180, 'propagateTags': 'TASK_DEFINITION',
        'deploymentConfiguration': {'deploymentCircuitBreaker': {'enable': True, 'rollback': True},
                                    'maximumPercent': 200, 'minimumHealthyPercent': 100},
        'networkConfiguration': {'awsvpcConfiguration': {'subnets': out['TaskSubnets'].split(','),
                                                         'securityGroups': [out['TaskSecurityGroup']],
                                                         'assignPublicIp': 'ENABLED'}},
        'loadBalancers': [{'targetGroupArn': out[cfg['target']], 'containerName': name, 'containerPort': cfg['port']}],
        'tags': [{'key': 'Project', 'value': 'M324-RefCard05'}],
    }
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
        json.dump(config, f)
    aws('ecs', 'create-service', '--cli-input-json', f'file://{f.name}')


def wait_for_rollout(service, task_arn, out):
    cluster, name = out['ClusterName'], f'biztrips-{service}'
    deadline, seen = time.time() + ROLLOUT_TIMEOUT_S, set()
    while time.time() < deadline:
        svc = aws('ecs', 'describe-services', '--cluster', cluster, '--services', name)['services'][0]
        for event in reversed(svc['events'][:10]):
            if event['id'] not in seen:
                seen.add(event['id'])
                log(f'  [ecs] {event["createdAt"]} {event["message"]}')
        ours = [d for d in svc['deployments'] if d['taskDefinition'] == task_arn]
        if not ours:
            fail(f'{name}: deployment of {task_arn} disappeared - the circuit breaker rolled back. '
                 f'Current task definition: {svc["taskDefinition"]}')
        deployment = ours[0]
        state = deployment.get('rolloutState')
        log(f'  rollout {state}: running {deployment["runningCount"]}/{deployment["desiredCount"]}, '
            f'failed tasks {deployment.get("failedTasks", 0)}')
        if state == 'COMPLETED' and deployment['status'] == 'PRIMARY' and len(svc['deployments']) == 1:
            return svc
        if state == 'FAILED':
            stopped = aws('ecs', 'list-tasks', '--cluster', cluster, '--service-name', name,
                          '--desired-status', 'STOPPED')['taskArns'][:3]
            reasons = []
            if stopped:
                for task in aws('ecs', 'describe-tasks', '--cluster', cluster, '--tasks', *stopped)['tasks']:
                    reasons.append(task.get('stoppedReason', '?'))
            fail(f'{name}: rollout FAILED ({deployment.get("rolloutStateReason")}). '
                 f'Stopped task reasons: {reasons}. ECS rolled back to the previous version. '
                 f'Check CloudWatch log group {out["LogGroup"]}.')
        time.sleep(15)
    fail(f'{name}: rollout not completed within {ROLLOUT_TIMEOUT_S // 60} minutes')


def fetch(url):
    request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'refcard05-deploy-check'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.read().decode()


def verify(service, version, out):
    """The new version must be served through the ALB 5 times in a row (old tasks drained)."""
    base = out['Endpoint']
    if service == 'backend':
        url, check = base + '/actuator/info', lambda body: json.loads(body)['app']['version'] == version
        health = base + '/actuator/health/readiness'
    else:
        url, check = base + '/version.json', lambda body: json.loads(body)['version'] == version
        health = base + '/health'
    deadline, streak, last = time.time() + VERIFY_TIMEOUT_S, 0, ''
    while time.time() < deadline:
        try:
            status, body = fetch(url)
            health_status, health_body = fetch(health)
            ok = status == 200 and health_status == 200 and check(body)
            last = f'{url} -> {body.strip()[:200]} | {health} -> {health_body.strip()[:120]}'
        except (urllib.error.URLError, ValueError, KeyError, TimeoutError) as ex:
            ok, last = False, f'{url} -> {ex}'
        streak = streak + 1 if ok else 0
        log(f'  verify {"OK" if ok else "waiting"} ({streak}/5): {last}')
        if streak >= 5:
            return last
        time.sleep(3 if ok else 10)
    fail(f'{service}: version {version} not served by {base} within {VERIFY_TIMEOUT_S // 60} minutes. Last: {last}')


def main():
    if len(sys.argv) != 4 or sys.argv[1] not in SERVICES:
        raise SystemExit('usage: ecs-deploy.py <backend|frontend> <image-uri> <version>')
    service, image, version = sys.argv[1:]
    region = os.environ.get('AWS_REGION', 'us-east-1')
    stack = os.environ.get('M324_STACK', 'bbw-m324-refcard05')
    out = stack_outputs(stack)

    task_arn = register_task_definition(service, image, version, out, region)
    create_or_update_service(service, task_arn, out)
    svc = wait_for_rollout(service, task_arn, out)
    evidence = verify(service, version, out)

    result = {'service': svc['serviceName'], 'cluster': out['ClusterName'], 'image': image, 'version': version,
              'taskDefinition': task_arn.split('/')[-1], 'runningCount': svc['runningCount'],
              'url': out['Endpoint'], 'verification': evidence}
    log(json.dumps(result, indent=2))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a') as f:
            f.write(f'### ECS deployment `{result["service"]}` verified\n\n| | |\n|---|---|\n')
            for key in ('cluster', 'image', 'version', 'taskDefinition', 'runningCount', 'url'):
                f.write(f'| {key} | `{result[key]}` |\n')
            f.write(f'| check | `{evidence}` |\n\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f'url={out["Endpoint"]}\n')


if __name__ == '__main__':
    main()
