### Class work development procedure

The class work codes from canvas needs some alterations and i have made it below in a proper sequential manner.

**AWS install**

```
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Provide credentials**

```
aws configure
```

**EKSCTL Install**

```
# for ARM systems, set ARCH to: `arm64`, `armv6` or `armv7`
ARCH=amd64
PLATFORM=$(uname -s)_$ARCH

curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$PLATFORM.tar.gz"

# (Optional) Verify checksum
curl -sL "<https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_checksums.txt>" | grep $PLATFORM | sha256sum --check

tar -xzf eksctl_$PLATFORM.tar.gz -C /tmp && rm eksctl_$PLATFORM.tar.gz

sudo mv /tmp/eksctl /usr/local/bin
```

**Set the default ssh-gen key in local**

This default ssh key is used by aws for default ssh login

```
ssh-keygen -t rsa -b 4096
```

**Install kubectl for aws eks in your local**

```
curl -O https://s3.us-west-2.amazonaws.com/amazon-eks/1.32.0/2024-12-20/bin/linux/amd64/kubectl

chmod +x ./kubectl

mkdir -p $HOME/bin && cp ./kubectl $HOME/bin/kubectl && export PATH=$HOME/bin:$PATH
```


Go into `eks-dev-cluster-config` folder

### Create cluster
Go into `eks-setup/cluster-config` folder

```
eksctl create cluster -f eks-cluster.yaml
```


Check instances from ec2

```
ssh ec2-user@43.204.212.5
kubectl config view
kubectl get all
```

#### Skipping first example (eks-dev-src-0)

#### Enable OIDC on your EKS Cluster

- `eksctl utils associate-iam-oidc-provider --region ap-south-1 --cluster basic-cluster-ap --approve`

- `curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/v2.11.0/docs/install/iam_policy.json`

- `aws iam create-policy --policy-name AWSLoadBalancerControllerIAMPolicy --policy-document file://iam-policy.json`


Create IAM Role for Service Account (IRSA)

```
eksctl create iamserviceaccount --cluster=basic-cluster-ap --namespace=kube-system --name=aws-load-balancer-controller  --attach-policy-arn=arn:aws:iam::306093656765:policy/AWSLoadBalancerControllerIAMPolicy --override-existing-serviceaccounts  --region ap-south-1  --approve
```

#### Install the AWS Load Balancer Controller using HELM

```
helm repo add eks https://aws.github.io/eks-charts
helm repo update
helm install aws-load-balancer-controller eks/aws-load-balancer-controller -n kube-system --set clusterName=basic-cluster-ap --set serviceAccount.create=false --set serviceAccount.name=aws-load-balancer-controller
```

verify load balancer
```
kubectl get all -n kube-system
```

Optional: Scale nodegroup

```
eksctl scale nodegroup --cluster=basic-cluster-ap --nodes=2 ng-dedicated-1 --nodes-max=4
```

Go into `eks-dev-src-1` folder

**Kubernetes dashboard**

Use this and fix metric-server api error if u use genric one

`https://medium.com/@cloudspinx/fix-error-metrics-api-not-available-in-kubernetes-aa10766e1c2f`

only then u can get output for ```kubectl top node``


```
helm repo add kubernetes-dashboard https://kubernetes.github.io/dashboard/
helm upgrade --install kubernetes-dashboard kubernetes-dashboard/kubernetes-dashboard --create-namespace --namespace kubernetes-dashboard
```

Create services

```
kubectl apply -f .
```
*Note: eks-admin.yaml is also present inside it

Create service account and RBAC

```
kubectl apply -f .
```
Check running and health and infer in /docs
```
kubectl delete -f .
```

Go into `eks-dev-src-2` folder (spot instance update)

```
kubectl apply -f .
```
Check running and health and infer in /docs
```
kubectl delete -f .
```

dashboard
```
kubectl -n kubernetes-dashboard create token admin-user

kubectl -n kubernetes-dashboard port-forward svc/kubernetes-dashboard-kong-proxy 8443:443
```

### Cluster Autoscaler 

Go into `eks-dev-cluster-config`

```
eksctl utils associate-iam-oidc-provider --region ap-south-1 --cluster basic-cluster --approve
```

```
aws iam create-policy --policy-name AWSClusterAutoScalerIAMPolicy --policy-document file://cas-iam-policy.json
```

```
eksctl create iamserviceaccount --cluster=basic-cluster-ap --namespace=kube-system  --name=cluster-autoscaler --attach-policy-arn=arn:aws:iam::306093656765:policy/AWSClusterAutoScalerIAMPolicy --override-existing-serviceaccounts --region ap-south-1 --approve
```


```
wget https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml
```

Do necessary modification

```
kubectl apply -f cluster-autoscaler-autodiscover.yaml
```



Now add a new nodegroup: ng-spot-4 to eks-cluster.yaml and then delete the old ng-spot-1

```
eksctl delete nodegroup --cluster basic-cluster --name ng-spot-3
```

verify it with
```
eksctl get nodegroup --cluster basic-cluster-ap
```

Wait and check after deletion of ng-spot-3 proceed next

```
  - name: ng-spot-4
    instanceType: t3a.medium
    minSize: 0
    maxSize: 5
    desiredCapacity: 0
    spot: true
    labels:
      role: spot
    propagateASGTags: true
    iam:
      withAddonPolicies:
        autoScaler: true
```

verify it with
```
eksctl get nodegroup --cluster basic-cluster-ap
```

Wait for complete deletion of ng-spot-1 for 3 minutes

- Go to "http://k8s-default-classifi-18da2b317c-1112532225.ap-south-1.elb.amazonaws.com/" loadbalancer url and go to "/docs" and verify infer and health

- Use this and fix metric-server api error [medium-blog](https://medium.com/@cloudspinx/fix-error-metrics-api-not-available-in-kubernetes-aa10766e1c2f)only then u can get output for `kubectl top node`

wait for some time like 5 minutes if the pods are pending. else recreate the nodegroup if needed and proceed

### Horizontal Pod Autoscaler (HPA)

Add the `HorizontalPodAutoscaler` yaml file to classifer.yaml

- `kubectl apply -f classifier.yaml`

- `kubectl describe hpa classifier-hpa`

it should show some warning

Testing the request script

```
python test_requests.py --url http://k8s-default-classifi-18da2b317c-748745984.ap-south-1.elb.amazonaws.com --requests 1 --workers 1
```
Check these commands if its working fine. else google and fix it
eg: for `kubectl top pod` you need metric server api

- `kubectl top pod`

- `kubectl get hpa classifier-hpa`

- `kubectl get node`


#### Check horizontal scaling

```
python test_requests.py --url http://k8s-default-classifi-18da2b317c-748745984.ap-south-1.elb.amazonaws.com --requests 200 --workers 20
```
- I have set the threshold to 50% and You would be able to see that the replicas and nodes would have increased to replica=10 and additional two nodes would have been added
Also added "resources:" for model-server container. without that the Horizontalautoscaler 
is unable to fetch the cpu utilization metric

- Check below three commands periodically it will increase the pods/replicas

  - `kubectl top pod`

  - `kubectl get hpa classifier-hpa`

  - `kubectl get node`


After 10 minutes of time and python script has ran successfully all the replicas scales down back to normal.

### Deletion Process

- `kubectl delete pod --field-selector="status.phase==Failed"`


Delete kubectl resources

- `kubectl delete all --all`

Delete cluster

- `eksctl delete cluster --name basic-cluster-ap --region ap-south-1`


- Go to cloudformation and check if all are deleted that are created when u started u r work.
- Remeber dont believe "Deletion in progress" it may get failed so wait and make sure all the resources are completely deleted in cloud formation
- Delete the loadbalancers
- Check the ec2 instance dashboard, spotrequest, autocluster group, loadbalancers and enure all are closed/terminated/deleted


TODO: add a proper commands for eks-dev-src-0 i.e the first `vision.py` file
