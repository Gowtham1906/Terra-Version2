provider "aws" {
  region = var.aws_region
}

module "vpc" {
  source = "../Parent_Module"

  vpc_configs          = var.vpc_configs
  existing_vpc_ids     = var.existing_vpc_ids
  region               = var.aws_region
}

terraform {
  backend "s3" {
    bucket = "my-infra-bucket-161024"
    key    = "terraform/terraform.tfstate"
    region = "us-east-1" 
  }
}



#Updated main.tf
resource "aws_vpc" "my_existing_vpc" {
  for_each              = var.imported_vpc_configs
  cidr_block            = each.value.cidr_block
  enable_dns_support    = each.value.enable_dns_support
  enable_dns_hostnames  = each.value.enable_dns_hostnames
  tags                  = each.value.tags
}
