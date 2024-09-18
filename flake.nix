{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
  };
  outputs = {...}@inputs:
  inputs.flake-utils.lib.eachDefaultSystem (system: let
    pkgs = (import inputs.nixpkgs) {
      inherit system;
      config = {
        allowUnfree = true;
      };
    };
    in
    {
      devShells = rec {
        docker-python = pkgs.mkShell {
          packages = with pkgs; [
            docker-compose
            docker
            podman-compose
            podman
            python3
            openssl
            postman
            dig
            pgadmin4-desktopmode
          ];
        };
        default = docker-python;
      };
      apps = rec {
        pgadmin = {
          type = "app";
          program = "${pkgs.pgadmin4-desktopmode}/bin/pgadmin4";
        };
        default = pgadmin;
      };
    }
  );
}