import subprocess
import hcl2
import os
import json
import boto3

def get_module_path():
    return os.path.dirname(os.path.abspath(__file__))

def fetch_vpc_details(vpc_id, variables):
    """Fetch VPC details from AWS using the given VPC ID."""
    region = variables.get('aws_region', '')  # Get region from variables
    ec2_client = boto3.client('ec2', region_name=region)
    response = ec2_client.describe_vpcs(VpcIds=[vpc_id])
    
    if response['Vpcs']:
        vpc = response['Vpcs'][0]
        cidr_block = vpc['CidrBlock']
        tags = {tag['Key']: tag['Value'] for tag in vpc.get('Tags', [])}
        return cidr_block, tags
    else:
        raise Exception(f"VPC with ID {vpc_id} not found.")

def append_to_tfvars(module_path, vpc_id, cidr_block, tags):
    """Append imported VPC configuration to terraform.tfvars."""
    tfvars_path = os.path.join(module_path, "terraform.tfvars")

    # Prepare new content
    new_content = f"""
#Updated terraform.tfvars
imported_vpc_configs = {{
  "{vpc_id}" = {{
    cidr_block           = "{cidr_block}"
    enable_dns_support   = true
    enable_dns_hostnames = true
    tags = {json.dumps(tags, indent=4)}
  }}
}}
"""
    # Check if terraform.tfvars already has imported_vpc_configs
    if os.path.exists(tfvars_path):
        with open(tfvars_path, "r") as f:
            existing_content = f.read()
        
        # If the section already exists, append to it; otherwise, just add the new content
        if "imported_vpc_configs" in existing_content:
            existing_content = existing_content.replace('imported_vpc_configs = {', f'imported_vpc_configs = {{\n  "{vpc_id}" = {{\n    cidr_block = "{cidr_block}",\n    enable_dns_support = true,\n    enable_dns_hostnames = true,\n    tags = {json.dumps(tags, indent=4)}\n  }}\n')
        else:
            existing_content += new_content
        
        with open(tfvars_path, "w") as f:
            f.write(existing_content)
    else:
        with open(tfvars_path, "w") as f:
            f.write(new_content)

    print(f"Appended imported VPC {vpc_id} configuration to terraform.tfvars.")

def update_main_tf(module_path):
    """Update main.tf with a single VPC resource using for_each."""
    main_tf_path = os.path.join(module_path, "main.tf")
    
    vpc_resource = """
#Updated main.tf
resource "aws_vpc" "my_existing_vpc" {
  for_each              = var.imported_vpc_configs
  cidr_block            = each.value.cidr_block
  enable_dns_support    = each.value.enable_dns_support
  enable_dns_hostnames  = each.value.enable_dns_hostnames
  tags                  = each.value.tags
}
"""

    # Check if main.tf already has the VPC resource configuration
    if os.path.exists(main_tf_path):
        with open(main_tf_path, "r") as f:
            existing_content = f.read()
        
        if "my_existing_vpc" not in existing_content:
            # Append the new VPC resource to main.tf
            with open(main_tf_path, "a") as f:
                f.write(vpc_resource)
            print("Appended VPC resource to main.tf.")
        else:
            print("VPC resource already exists in main.tf.")
    else:
        with open(main_tf_path, "w") as f:
            f.write(vpc_resource)
        print("Created main.tf and added VPC resource configuration.")

def update_variables_tf(module_path):
    """Append imported VPC configurations to variables.tf if not exists."""
    variables_tf_path = os.path.join(module_path, "variables.tf")
    
    new_variable = """
#Updated variables.tf
variable "imported_vpc_configs" {
  description = "Imported VPC configurations"
  type = map(object({
    cidr_block           = string
    enable_dns_support   = bool
    enable_dns_hostnames = bool
    tags                 = map(string)
  }))
  default = {}
}
"""
    
    # Check if the variable already exists in the file
    if not os.path.exists(variables_tf_path):
        with open(variables_tf_path, "w") as f:
            f.write(new_variable)
        print("Created variables.tf and added imported_vpc_configs variable.")
        return

    with open(variables_tf_path, "r") as f:
        existing_content = f.read()
    
    if "variable \"imported_vpc_configs\"" not in existing_content:
        # Append the new variable to variables.tf
        with open(variables_tf_path, "a") as f:
            f.write(new_variable)
        print("Appended imported_vpc_configs variable to variables.tf")
    else:
        print("imported_vpc_configs variable already exists in variables.tf")

def main(module_path):
    """Main function to run the script."""
    # First, read the existing VPC IDs from terraform.tfvars
    tfvars_path = os.path.join(module_path, 'terraform.tfvars')
    
    if not os.path.exists(tfvars_path):
        print("Error: terraform.tfvars file does not exist.")
        exit(1)
    
    with open(tfvars_path, 'r') as f:
        variables = hcl2.load(f)

    existing_vpc_ids = variables.get('existing_vpc_ids', [])
    
    if not existing_vpc_ids:
        print("Error: No VPC IDs found in terraform.tfvars.")
        exit(1)

    for existing_id in existing_vpc_ids:
        try:
            cidr_block, tags = fetch_vpc_details(existing_id, variables)  # Pass variables here
        except Exception as e:
            print(f"Error fetching VPC details for {existing_id}: {e}")
            continue

        # Check if the VPC details already exist in terraform.tfvars
        with open(tfvars_path, 'r') as f:
            tfvars_content = f.read()
        if f'"{existing_id}" =' in tfvars_content:
            print(f"VPC {existing_id} has already been imported. Skipping update.")
            continue

        append_to_tfvars(module_path, existing_id, cidr_block, tags)

    update_main_tf(module_path)
    update_variables_tf(module_path)

    # Initialize Terraform
    try:
        print("Initializing Terraform...")        
        subprocess.run(['terraform', 'init'], check=True)
    except subprocess.CalledProcessError as e:
        print("Error during Terraform initialization:")
        print(e.output)
        exit(1)

    # Import each VPC
    for existing_id in existing_vpc_ids:
        import_command = ['terraform', 'import', f'aws_vpc.my_existing_vpc["{existing_id}"]', existing_id]
        try:
            print(f"Importing VPC with ID: {existing_id}...")
            result = subprocess.run(import_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print("Import Output:", result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error during VPC import for {existing_id}:")
            print("Return code:", e.returncode)
            print("Command output:", e.output)
            print("Command error:", e.stderr)
            continue

    # Plan the changes
    try:
        print("Planning changes...")
        subprocess.run(['terraform', 'plan'], check=True)
    except subprocess.CalledProcessError as e:
        print("Error during Terraform plan:")
        print(e.output)
        exit(1)

    # Apply the changes
    try:
        print("Applying changes...")
        subprocess.run(['terraform', 'apply', '-auto-approve'], check=True)
    except subprocess.CalledProcessError as e:
        print("Error during Terraform apply:")
        print(e.output)
        exit(1)

    print("Import and VPC creation completed successfully.")

if __name__ == "__main__":
    module_path = get_module_path()
    main(module_path)
