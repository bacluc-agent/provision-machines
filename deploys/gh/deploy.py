from pyinfra import host

from operations.github_release_binary import github_release_binary

gh = host.data.gh

# renovate: datasource=github-releases depName=cli/cli
gh_version = "2.102.0"
gh_checksum = "7469124f706944133d6a169691dd1c6c3511b12e85878d255e044e2948df4c9b"

if gh["enabled"]:
    github_release_binary(
        url=f"https://github.com/cli/cli/releases/download/v{gh_version}/gh_{gh_version}_linux_amd64.tar.gz",
        binary_name="gh",
        checksum=gh_checksum,
        strip_components=2,
        tar_member=f"gh_{gh_version}_linux_amd64/bin/gh",
    )
