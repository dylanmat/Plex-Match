Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

docker compose build
docker compose --profile test run --rm test
