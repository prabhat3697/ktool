# ktool

Kubectl shortcuts + search + summaries for managing Kubernetes pods.

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
```
