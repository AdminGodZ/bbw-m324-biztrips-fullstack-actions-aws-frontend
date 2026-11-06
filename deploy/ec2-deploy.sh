#!/usr/bin/env bash
set -euo pipefail
: "${EC2_HOST:?}" "${EC2_USER:?}" "${EC2_SSH_KEY:?}" "${EC2_KNOWN_HOSTS:?}"
key_dir=$(mktemp -d)
runner_cidr=$(curl -fsS https://checkip.amazonaws.com)/32
cleanup() {
  rm -rf "$key_dir"
  aws ec2 revoke-security-group-ingress --group-id "$EC2_SECURITY_GROUP" --protocol tcp --port 22 --cidr "$runner_cidr" >/dev/null 2>&1 || true
}
trap cleanup EXIT
aws ec2 authorize-security-group-ingress --group-id "$EC2_SECURITY_GROUP" --protocol tcp --port 22 --cidr "$runner_cidr" >/dev/null

printf '%s\n' "$EC2_SSH_KEY" > "$key_dir/key"
printf '%s\n' "$EC2_KNOWN_HOSTS" > "$key_dir/known_hosts"
chmod 600 "$key_dir/"*
export RSYNC_RSH="ssh -i $key_dir/key -o UserKnownHostsFile=$key_dir/known_hosts -o StrictHostKeyChecking=yes"
rsync -az --delete -e "$RSYNC_RSH" dist/ "$EC2_USER@$EC2_HOST:/var/www/biztrips/"
$RSYNC_RSH "$EC2_USER@$EC2_HOST" 'sudo nginx -t && sudo systemctl reload nginx'
curl --fail --retry 5 --retry-delay 3 "http://$EC2_HOST/"
