# Build both image targets with the same inputs CI uses:
#   docker buildx bake                       # api and worker (group "default")
#   docker buildx bake api                   # API image only
#   docker buildx bake --set '*.args.VERSION=1.2.3' --set '*.args.REVISION=$(git rev-parse HEAD)'
# Override variables through the environment, for example
#   SOURCE_DATE_EPOCH=$(git log -1 --pretty=%ct) REVISION=$(git rev-parse HEAD) docker buildx bake
variable "VERSION" {
  default = "dev"
}

variable "REVISION" {
  default = "unknown"
}

variable "CREATED" {
  default = "unknown"
}

variable "SOURCE_DATE_EPOCH" {
  default = "0"
}

group "default" {
  targets = ["api", "worker"]
}

target "api" {
  context    = "."
  dockerfile = "infra/docker/app/Dockerfile"
  target     = "api"
  platforms  = ["linux/amd64"]
  tags       = ["portfolio-assistant-api:ci"]
  args = {
    VERSION           = VERSION
    REVISION          = REVISION
    CREATED           = CREATED
    SOURCE_DATE_EPOCH = SOURCE_DATE_EPOCH
  }
}

target "worker" {
  context    = "."
  dockerfile = "infra/docker/app/Dockerfile"
  target     = "worker"
  platforms  = ["linux/amd64"]
  tags       = ["portfolio-assistant-api-worker:ci"]
  args = {
    VERSION           = VERSION
    REVISION          = REVISION
    CREATED           = CREATED
    SOURCE_DATE_EPOCH = SOURCE_DATE_EPOCH
  }
}
