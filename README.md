# ktool

Kubectl shortcuts + search + summaries for managing Kubernetes resources.

## Installation

```bash
pip install -e .
```

## Commands

### `k` - List Pods

The main command to list and filter Kubernetes pods. Supports flexible argument ordering.

#### Basic Usage

```bash
# List all pods in default namespace
k

# List pods with optional 'pods' keyword
k pods

# Filter by service name (e.g., my-service)
k my-service

# Same as above, with explicit 'pods' keyword
k pods my-service
```

#### Options

- **Service Name** (positional argument): Filter pods by service name
  ```bash
  k my-service
  k pods my-service
  ```

- **`-n, --ns NAMESPACE`**: Specify namespace
  ```bash
  k -n production
  k my-service -n production
  k -n production my-service
  ```

- **`-s, --search PATTERN`**: Search pods by regex pattern
  ```bash
  k --search "api-.*"
  k -s "worker"
  ```

- **`--summary`**: Show summary statistics
  ```bash
  k --summary
  k my-service --summary
  ```

- **`--bad`**: Show only problematic pods (not Running or Succeeded)
  ```bash
  k --bad
  k my-service --bad
  ```

- **`--show-command, --showCommand`**: Show the actual kubectl command being executed
  ```bash
  k --show-command
  k my-service --show-command
  k --showCommand my-service --summary
  ```

#### Examples

```bash
# List all pods with summary
k --summary

# Filter by service and show summary
k my-service --summary

# Search for pods matching pattern
k --search "api-server"

# Show only problematic pods in specific namespace
k --bad -n production

# Combine multiple options (flexible ordering)
k my-service -n production --summary
k -n production --summary my-service
k pods my-service --summary -n production

# Show the actual kubectl command being executed
k my-service --show-command
k --show-command --summary
```

### `k logs` - Get Pod Logs

Get logs from a pod. Can use service name to automatically find the pod.

```bash
# Get logs from a pod
k logs my-pod

# Get logs from a service (finds first matching pod)
k logs my-service

# Follow logs
k logs my-pod --follow
k logs my-service -f

# Get last 100 lines
k logs my-pod --tail 100

# Get logs from a specific container
k logs my-pod -c container-name

# Get logs from previous instance
k logs my-pod --previous

# With namespace
k logs my-pod -n production

# Show the kubectl command
k logs my-pod --show-command
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace
- `-c, --container CONTAINER`: Container name
- `-f, --follow`: Follow log output
- `--tail N`: Number of lines to show from the end
- `-p, --previous`: Previous instance logs
- `--show-command, --showCommand`: Show the actual kubectl command

### `k describe` - Describe Resources

Describe a Kubernetes resource.

```bash
# Describe a pod
k describe pod/my-pod

# Describe a deployment
k describe deployment/my-deploy

# Describe a service
k describe service/my-svc

# With namespace
k describe pod/my-pod -n production

# Show the kubectl command
k describe pod/my-pod --show-command
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace
- `--show-command, --showCommand`: Show the actual kubectl command

### `k exec` - Execute Commands in Pods

Execute a command in a pod. Can use service name to automatically find the pod.

```bash
# Execute a command in a pod
k exec my-pod -- ls -la

# Execute in a service (finds first matching pod)
k exec my-service -- ps aux

# Interactive shell
k exec my-pod -it -- /bin/sh

# Execute in specific container
k exec my-pod -c container-name -- env

# With namespace
k exec my-pod -n production -- date

# Show the kubectl command
k exec my-pod --show-command -- ls
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace
- `-c, --container CONTAINER`: Container name
- `-i, --stdin`: Keep stdin open
- `-t, --tty`: Allocate a TTY
- `--show-command, --showCommand`: Show the actual kubectl command

### `k port-forward` - Port Forwarding

Forward local ports to a pod or service.

```bash
# Forward port 8080 to pod port 80
k port-forward pod/my-pod 8080:80

# Forward to service
k port-forward service/my-svc 8080:80

# Forward multiple ports
k port-forward pod/my-pod 8080:80 8443:443

# With namespace
k port-forward pod/my-pod 8080:80 -n production

# Show the kubectl command
k port-forward pod/my-pod 8080:80 --show-command
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace
- `--show-command, --showCommand`: Show the actual kubectl command

### `k get` - Get Resources

Get Kubernetes resources (pods, services, deployments, etc.).

```bash
# Get all pods
k get pods

# Get a specific pod
k get pods my-pod

# Get services
k get services

# Get deployments
k get deployments

# With namespace
k get pods -n production

# Custom output format
k get pods -o json
k get pods -o yaml
k get pods -o wide

# Show the kubectl command
k get pods --show-command
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace
- `-o, --output FORMAT`: Output format (json, yaml, wide, etc.)
- `--show-command, --showCommand`: Show the actual kubectl command

### `k delete` - Delete Resources

Delete Kubernetes resources.

```bash
# Delete a pod
k delete pod/my-pod

# Delete a deployment
k delete deployment/my-deploy

# Force delete
k delete pod/my-pod --force

# With grace period
k delete pod/my-pod --grace-period 30

# With namespace
k delete pod/my-pod -n production

# Show the kubectl command
k delete pod/my-pod --show-command
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace
- `--force`: Force deletion
- `--grace-period SECONDS`: Grace period in seconds
- `--show-command, --showCommand`: Show the actual kubectl command

### `k top` - Resource Usage

Display resource usage (CPU/memory) for pods or nodes.

```bash
# Show pod resource usage
k top pods

# Show specific pod
k top pods my-pod

# Show node resource usage
k top nodes

# With namespace
k top pods -n production

# Show the kubectl command
k top pods --show-command
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace (for pods)
- `--show-command, --showCommand`: Show the actual kubectl command

### `k rollout` - Manage Rollouts

Manage rollouts for deployments, daemonsets, and statefulsets.

```bash
# Restart a deployment
k rollout restart deployment/my-deploy

# Check rollout status
k rollout status deployment/my-deploy

# View rollout history
k rollout history deployment/my-deploy

# View specific revision
k rollout history deployment/my-deploy --revision 3

# Undo rollout
k rollout undo deployment/my-deploy

# Undo to specific revision
k rollout undo deployment/my-deploy --revision 2

# Pause rollout
k rollout pause deployment/my-deploy

# Resume rollout
k rollout resume deployment/my-deploy

# With namespace
k rollout restart deployment/my-deploy -n production

# Show the kubectl command
k rollout restart deployment/my-deploy --show-command
```

Options:
- `-n, --ns NAMESPACE`: Specify namespace
- `--revision N`: Revision number (for history/undo)
- `--show-command, --showCommand`: Show the actual kubectl command

### `kctx` - Context Management

Manage kubectl contexts with aliases.

#### Commands

- **`kctx use ALIAS`**: Switch to a context
  ```bash
  kctx use prod
  kctx use staging
  kctx use prod --show-command
  ```
  If `ALIAS` is defined in the `contexts` section of your config, it will use the mapped context name. Otherwise, it uses the alias directly as the context name.
  
  Options:
  - `--show-command, --showCommand`: Show the actual kubectl command being executed

- **`kctx show`**: Show current kubectl context
  ```bash
  kctx show
  kctx show --show-command
  ```
  
  Options:
  - `--show-command, --showCommand`: Show the actual kubectl command being executed

## Configuration

Create a configuration file at `~/.ktool/config.yaml`:

```yaml
default_namespace: production

contexts:
  prod: gke_myproject_production_cluster
  staging: gke_myproject_staging_cluster
  dev: gke_myproject_dev_cluster

services:
  web: web-service
  api: api-server
  worker: worker-service
```

### Configuration Options

- **`default_namespace`**: Default namespace to use when `-n/--ns` is not specified (default: `default`)
- **`contexts`**: Map of aliases to actual kubectl context names
- **`services`**: Map of service tags to actual service names (allows using short names like `web` instead of `web-service`)

## Output

The `k` command displays a table with:
- **Pod**: Pod name
- **State**: Current pod state (Running, Pending, Error, etc.)
- **Bad**: Indicates if the pod is in a problematic state (not Running or Succeeded)

When `--summary` is used, additional statistics are shown:
- State counts (e.g., `Running=5, Pending=2`)
- Total pods matched
- Number of problematic pods

## Examples

```bash
# Basic pod listing
k

# Filter by service
k my-service

# With summary
k my-service --summary

# Search with regex
k --search ".*-api-.*"

# Only show problematic pods
k --bad

# Different namespace
k -n staging my-service

# Switch context
kctx use prod

# Show current context
kctx show

# Get logs from a pod
k logs my-pod

# Describe a resource
k describe pod/my-pod

# Execute command in pod
k exec my-pod -- ls -la

# Port forward
k port-forward pod/my-pod 8080:80

# Get other resources
k get services
k get deployments

# Delete a resource
k delete pod/my-pod

# Check resource usage
k top pods

# Restart deployment
k rollout restart deployment/my-deploy
```
