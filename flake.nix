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
        init-repo = {
          type = "app";
          program = "${pkgs.writeShellScriptBin "init.sh" ''
            upsearch () {
            local slashes=$\{PWD//[^\/]/}
            local directory=$(pwd)
            for (( n=$\{#slashes}; n>0; --n ))
              do
                test -e "$directory/$1" && cd $directory 
                directory="$directory/.."
              done
            }

            upsearch flake.nix

            mkdir ssl
            cd ssl

            openssl req -newkey rsa:4096 -x509 -sha512 -days 365 -nodes -out localhost_bundle.crt -keyout localhost.key -subj "/C=US/ST=Ohio/L=Cleveland /O=AI4EDU/OU=dev/CN=au4edudev/emailAddress=."
            openssl genrsa 512 > privateKey.pem
            openssl rsa -in privateKey.pem -pubout > publicKey.pem
          ''}/bin/init.sh";
        };
        compose = {
          type = "app";
          program = "${pkgs.writeShellScriptBin "start-compose.sh" ''
            ${pkgs.docker-compose}/bin/docker-compose up --build
          ''}/bin/start-compose.sh";
        };
        default = pgadmin;
      };
    }
  );
}