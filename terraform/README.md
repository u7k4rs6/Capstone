# Terraform: VPC + EKS

Creates a VPC (2 public + 2 private subnets, 1 NAT gateway) and an EKS cluster with one managed node group. The EBS CSI driver add-on is included so the Postgres PVC can get a gp3 volume.

```bash
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
$(terraform output -raw configure_kubectl)
kubectl get nodes

# when you're done (EKS + NAT cost money by the hour)
terraform destroy
```

Before `terraform destroy`, uninstall ingress-nginx (or delete the `stockroom` ArgoCD app and the ingress-nginx release) so the AWS load balancer it created goes away. Otherwise the VPC delete can hang on leftover ENIs.

State is local. For a team you'd move it to S3 with a lock table.
