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
            aiohttp
            aiosignal
            alembic
            annotated-types
            anthropic
            anyio
            async-timeout
            attrs
            boto3
            boto3-stubs
            mypy-boto3-dynamodb
            mypy-boto3-s3
            botocore
            certifi
            cffi
            chardet
            charset-normalizer
            click
            cryptography
            dataclasses-json
            defusedxml
            distro
            dnspython
            email_validator
            fastapi
            fastapi-cli
            filelock
            frozenlist
            fsspec
            h11
            hiredis
            httpcore
            httptools
            httpx
            huggingface-hub
            idna
            jinja2
            jiter
            jmespath
            jsonpatch
            jsonpointer
            langchain
            (pkgs.callPackage ./langchain-anthropic.nix pkgs.python312Packages)
            langchain-community
            langchain-core
            langchain-openai
            # TODO: needs pinecone-client to work
            # langchain-pinecone
            langchain-text-splitters
            langsmith
            Mako
            markdown-it-py
            markupsafe
            marshmallow
            mdurl
            multidict
            mypy-extensions
            numpy
            openai
            orjson
            packaging
            # TODO: fix this package
            (pkgs.callPackage ./pinecone.nix pkgs.python312Packages)
            (pkgs.callPackage ./langchain-pinecone.nix pkgs.python312Packages)
            psycopg
            # psycopg-binary
            pycparser
            pydantic
            pydantic-core
            pygments
            pyjwt
            pypdf
            python-dateutil
            python-dotenv
            python-multipart
            pyyaml
            types-redis
            redis
            regex
            requests
            rich
            s3transfer
            shellingham
            six
            sniffio
            sqlalchemy
            sse-starlette
            starlette
            tenacity
            tiktoken
            tokenizers
            tqdm
            typer
            typing-inspect
            typing-extensions
            ujson
            urllib3
            uvicorn
            uvloop
            watchfiles
            websockets
            yarl
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
              # pgadmin4-desktopmode
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
      }
    );
}
