# Event-Tools

Automate handing of events and protocols.
Uses Cryptpad, Redmine and Discourse.

## Tech Stack

* [Python 3.8](https://www.python.org)
* Chromium / Chromedriver
* Build / dependency management: [Nix](https://nixos.org/nix)

## Using it

If you have installed the [Nix](https://nixos.org/nix), running the CLI script is easy.
Nix installs all dependencies including Chromium / Chromedriver.

1. Clone the repository with:
    ~~~Shell
    git clone https://github.com/Piratenpartei/event-tools
    ~~~
2. Enter the project root folder:
    ~~~Shell
    cd event-tools
    ~~~
3. Run the CLI script to see the available commands:
    ~~~Shell
    ./event-cli --help
    ~~~

- Running the Nix wrapper script ./event-cli takes some seconds.
  If you want to use the CLI regulary with shorter startup time, install it with:

  ~~~Shell
  nix-env -if .
  ~~~

If your shell is configured correctly (nix bin dir in PATH),
you should be able to run the event-cli command from anywhere.


## Development

### Quick Start

The shell environment for development can be prepared using the Nix Package Manager.
It includes Python, development / testing tools and dependencies for the project itself.
The following instructions assume that the Nix package manager is already installed, `nix-shell` is available in PATH.

1. Clone the repository with:
    ~~~Shell
    git clone https://github.com/Piratenpartei/event-tools
    ~~~
2. Enter nix shell in the project root folder to open a shell which is your dev environment:
    ~~~Shell
    cd event-tools
    nix-shell
    ~~~

## License

AGPLv3, see LICENSE

## Authors

* Tobias 'dpausp'

