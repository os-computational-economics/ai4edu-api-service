{
  inputs = {
    flake-utils.url = "github:numtide/flake-utils";
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";
    nixpkgs-treefmt.url = "github:nixos/nixpkgs/nixos-unstable";
    treefmt-nix.url = "github:numtide/treefmt-nix";
  };
  outputs = {...} @ inputs:
    inputs.flake-utils.lib.eachDefaultSystem (
      system: let
        pkgs = (import inputs.nixpkgs) {
          inherit system;
          config = {
            allowUnfree = true;
          };
        };
        pkgs-treefmt = (import inputs.nixpkgs-treefmt) {
          inherit system;
        };
        py = pkgs.python3.withPackages (python-pkgs:
          with python-pkgs; [
            anthropic
            boto3
            boto3-stubs
            mypy-boto3-dynamodb
            mypy-boto3-s3
            botocore
            chardet
            defusedxml
            fastapi
            fastapi-cli
            langchain
            langchain-community
            langchain-core
            langchain-openai
            (pkgs.callPackage ./nix/langchain-anthropic.nix pkgs.python312Packages)
            (pkgs.callPackage ./nix/langchain-pinecone.nix pkgs.python312Packages)
            openai
            pinecone-client
            psycopg
            pydantic
            pyjwt
            pypdf
            python-dotenv
            python-multipart
            redis
            types-redis
            requests
            sqlalchemy
            sse-starlette
            starlette
            uvicorn
          ]);
      in {
        devShells = rec {
          docker-python = pkgs.mkShell {
            packages = with pkgs; [
              docker-compose
              docker
              podman-compose
              podman
              py
              openssl
              fastapi-cli
              bruno
              pkgs-treefmt.bruno-cli
              openapi-generator-cli
              dig
              ruff
              basedpyright
            ];
          };
          default = docker-python;
        };
        formatter = let
          treefmtconfig = inputs.treefmt-nix.lib.evalModule pkgs-treefmt {
            projectRootFile = "flake.nix";
            programs = {
              alejandra.enable = true;
              ruff-format.enable = true;
              toml-sort.enable = true;
              yamlfmt.enable = true;
              mdformat.enable = true;
              shellcheck.enable = true;
              shfmt.enable = true;
            };
            settings.formatter.shellcheck.excludes = [".envrc"];
          };
        in
          treefmtconfig.config.build.wrapper;
        apps = rec {
          pgadmin = {
            type = "app";
            program = "${pkgs.pgadmin4-desktopmode}/bin/pgadmin4";
          };
          init-repo = {
            type = "app";
            program = "${pkgs.writeShellScriptBin "init.sh" ''
              upsearch () {
              local slashes=''${PWD//[^\/]/}
              local directory=$(pwd)
              for (( n=''${#slashes}; n>0; --n ))
                do
                  test -e "$directory/$1" && cd $directory
                  directory="$directory/.."
                done
              }

              upsearch flake.nix

              mkdir ssl
              cd ssl

              openssl req -newkey rsa:4096 -x509 -sha512 -days 365 -nodes -out localhost_bundle.crt -keyout localhost.key -subj "/C=US/ST=Ohio/L=Cleveland /O=AI4EDU/OU=dev/CN=localhost/emailAddress=."
              openssl genrsa 2048 > privateKey.pem
              openssl rsa -in privateKey.pem -pubout > publicKey.pem
            ''}/bin/init.sh";
          };
          compose = {
            type = "app";
            program = "${pkgs.writeShellScriptBin "start-compose.sh" ''
              upsearch () {
              local slashes=''${PWD//[^\/]/}
              local directory=$(pwd)
              for (( n=''${#slashes}; n>0; --n ))
                do
                  test -e "$directory/$1" && cd $directory
                  directory="$directory/.."
                done
              }

              upsearch flake.nix
              nix build .#docker
              podman load < result
              ${pkgs.podman-compose}/bin/podman-compose up --build --force-recreate
            ''}/bin/start-compose.sh";
          };
          generate = {
            type = "app";
            program = "${pkgs.writeShellScriptBin "start-compose.sh" ''
              upsearch () {
                local slashes=''${PWD//[^\/]/}
                local directory=$(pwd)
                for (( n=''${#slashes}; n>0; --n ))
                do
                  test -e "$directory/$1" && cd $directory
                  directory="$directory/.."
                done
              }

              upsearch flake.nix

              ${py}/bin/python get_openapi.py
              mkdir -p openapi
              cd openapi
              ${pkgs.openapi-generator-cli}/bin/openapi-generator-cli generate -g html2 -i ../openapi.yaml
              ${pkgs.openapi-generator-cli}/bin/openapi-generator-cli generate -g typescript-node -i ../openapi.yaml
            ''}/bin/start-compose.sh";
          };
          default = compose;
        };
        packages = rec {
          docker = pkgs.callPackage ./nix/docker.nix { inherit py; app = ./src; };
          default = docker;
        };
      }
    );
}
