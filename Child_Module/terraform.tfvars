aws_region = "us-east-1"

existing_vpc_ids = [
  "vpc-01483b6fe6b00af73", 
  "vpc-07bd81c8b6c7c9b6d"
]


vpc_configs = {
  "vpc" = {
    cidr_block           = "10.0.0.0/16"
    enable_dns_support   = true
    enable_dns_hostnames = true
    tags = {
      Name        = "Terra_Auto"
      Environment = "production"
    }
  }
}
