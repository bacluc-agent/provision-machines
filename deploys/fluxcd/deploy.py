import io

from pyinfra import host
from pyinfra.operations import files

from operations.user import get_user_name

user = get_user_name()

if host.data.fluxcd["enabled"]:
    # renovate: datasource=docker depName=ghcr.io/fluxcd/flux-cli
    flux_cli_version = "v2.2.3"
    flux_aliases = f"""alias flux='docker run --rm -it \\
  --user $UID \\
  --volume $KUBECONFIG:/kubeconfig \\
  --volume $PWD:/workspace \\
  --workdir $PWD:/workspace \\
  ghcr.io/fluxcd/flux-cli:${{FLUX_CLI_VERSION:-{flux_cli_version}}} --kubeconfig=/kubeconfig'

alias fluxa='docker run --rm -it \\
  --user $UID \\
  --volume $KUBECONFIG:/kubeconfig \\
  --volume $PWD:/workspace \\
  --workdir $PWD:/workspace \\
  ghcr.io/fluxcd/flux-cli:${{FLUX_CLI_VERSION:-{flux_cli_version}}} --kubeconfig=/kubeconfig --as "system:admin"'
"""

    files.put(
        name="Add flux cli aliases",
        src=io.StringIO(flux_aliases),
        dest=f"/home/{user}/.bash_aliases.d/flux-aliases.sh",
        user=user,
        group=user,
        mode="644",
    )
