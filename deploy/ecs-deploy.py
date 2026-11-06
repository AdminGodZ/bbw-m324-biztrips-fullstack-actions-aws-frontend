#!/usr/bin/env python3
"""Render a task from deployed stack outputs; create/update service and verify it."""
import json, os, subprocess, sys, urllib.request

service, image = sys.argv[1:]
if service not in ('backend','frontend'): raise SystemExit('Invalid service')
region=os.environ.get('AWS_REGION','us-east-1')
stack=os.environ.get('M324_STACK','bbw-m324-biztrips-refcard03-04')
def aws(*args):
    return json.loads(subprocess.check_output(['aws',*args,'--region',region,'--output','json']))
output=aws('cloudformation','describe-stacks','--stack-name',stack)['Stacks'][0]['Outputs']
values={o['OutputKey']:o['OutputValue'] for o in output}
port=8080 if service=='backend' else 80
name='biztrips-'+service
container={'name':name,'image':image,'essential':True,'portMappings':[{'containerPort':port,'protocol':'tcp'}],
 'logConfiguration':{'logDriver':'awslogs','options':{'awslogs-group':values['LogGroup'],'awslogs-region':region,'awslogs-stream-prefix':service}},
 'healthCheck':{'command':['CMD-SHELL',f'wget -q -O /dev/null http://127.0.0.1:{port}/'+('actuator/health' if service=='backend' else 'health')+' || exit 1'],'interval':15,'timeout':5,'retries':5,'startPeriod':90 if service=='backend' else 15}}
if service=='backend':
    container['environment']=[{'name':'SPRING_PROFILES_ACTIVE','value':'mariadb'},
      {'name':'DB_URL','value':'jdbc:mariadb://'+values['DBEndpoint']+':3306/db_biztrips?sslMode=verify-full&serverSslCert=/app/rds-ca-bundle.crt'},
      {'name':'DB_USER','value':'biztrips'}]
    container['secrets']=[{'name':'DB_PASSWORD','valueFrom':values['DBSecretArn']+':password::'}]
else:
    container['environment']=[{'name':'BACKEND_ORIGIN','value':values['Endpoint']}]
task={'family':'bbw-m324-biztrips-'+service,'networkMode':'awsvpc','requiresCompatibilities':['FARGATE'],
 'cpu':'512' if service=='backend' else '256','memory':'1024' if service=='backend' else '512',
 'executionRoleArn':values['RoleArn'],'taskRoleArn':values['RoleArn'],
 'runtimePlatform':{'cpuArchitecture':'X86_64','operatingSystemFamily':'LINUX'},'containerDefinitions':[container]}
taskfile='/tmp/m324-task-'+service+'.json'
with open(taskfile,'w') as f: json.dump(task,f,indent=2)
arn=aws('ecs','register-task-definition','--cli-input-json','file://'+taskfile)['taskDefinition']['taskDefinitionArn']
cluster=values['ClusterName']
existing=aws('ecs','describe-services','--cluster',cluster,'--services',name)['services']
if existing and existing[0]['status']!='INACTIVE':
    aws('ecs','update-service','--cluster',cluster,'--service',name,'--task-definition',arn)
else:
    config={'cluster':cluster,'serviceName':name,'taskDefinition':arn,'desiredCount':1,'launchType':'FARGATE',
     'healthCheckGracePeriodSeconds':180,
     'deploymentConfiguration':{'deploymentCircuitBreaker':{'enable':True,'rollback':True},'maximumPercent':200,'minimumHealthyPercent':100},
     'networkConfiguration':{'awsvpcConfiguration':{'subnets':values['TaskSubnets'].split(','),'securityGroups':[values['TaskSecurityGroup']],'assignPublicIp':'ENABLED'}},
     'loadBalancers':[{'targetGroupArn':values['BackendTarget' if service=='backend' else 'FrontendTarget'],'containerName':name,'containerPort':port}]}
    with open('/tmp/m324-service-'+service+'.json','w') as f: json.dump(config,f)
    aws('ecs','create-service','--cli-input-json','file:///tmp/m324-service-'+service+'.json')
subprocess.run(['aws','ecs','wait','services-stable','--cluster',cluster,'--services',name,'--region',region],check=True)
subprocess.run(['aws','elbv2','wait','target-in-service','--target-group-arn',values['BackendTarget' if service=='backend' else 'FrontendTarget'],'--region',region],check=True)
# Seed the demo database once before starting the second backend task.
aws('ecs','update-service','--cluster',cluster,'--service',name,'--desired-count','2')
subprocess.run(['aws','ecs','wait','services-stable','--cluster',cluster,'--services',name,'--region',region],check=True)
subprocess.run(['aws','elbv2','wait','target-in-service','--target-group-arn',values['BackendTarget' if service=='backend' else 'FrontendTarget'],'--region',region],check=True)
deployed=aws('ecs','describe-services','--cluster',cluster,'--services',name)['services'][0]
if deployed['taskDefinition']!=arn or deployed['runningCount']!=deployed['desiredCount']:
    raise SystemExit('ECS rolled back or failed to reach the requested deployment')
url=values['Endpoint']+('/actuator/health' if service=='backend' else '/')
with urllib.request.urlopen(url,timeout=30) as response:
    if response.status!=200: raise SystemExit('Deployment health check failed')
print(json.dumps({'service':name,'taskDefinition':arn,'runningCount':deployed['runningCount'],'url':url},indent=2))
