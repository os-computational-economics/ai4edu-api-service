{
  lib,
  buildPythonPackage,
  dnspython,
  fetchPypi,
  loguru,
  numpy,
  poetry-core,
  python-dateutil,
  pythonOlder,
  pythonRelaxDepsHook,
  pyyaml,
  requests,
  setuptools,
  tqdm,
  typing-extensions,
  urllib3,
  ...
}: let
  pinecone-plugin-inference = buildPythonPackage rec {
    pname = "pinecone-plugin-inference";
    version = "2.0.0";
    pyproject = true;

    disabled = pythonOlder "3.8";

    src = fetchPypi {
      pname = "pinecone_plugin_inference";
      inherit version;
      hash = "sha256-spcJzV2Cgp+NA2Gj9bUdq2ItpZUzV4CXvgTnPu7PPuU=";
    };

    pythonRemoveDeps = ["pinecone-plugin-interface"];
    build-system = [
      setuptools
      poetry-core
    ];
  };
  pinecone-plugin-interface = buildPythonPackage rec {
    pname = "pinecone-plugin-interface";
    version = "0.0.7";
    pyproject = true;

    disabled = pythonOlder "3.8";

    src = fetchPypi {
      pname = "pinecone_plugin_interface";
      inherit version;
      hash = "sha256-uOZnXkGEczOqE5I8xE2qP4VnbXFXMkaC3BZAWIqYKEY=";
    };

    pythonRemoveDeps = ["pinecone-plugin-inference"];
    build-system = [
      setuptools
      poetry-core
    ];
  };
in
  buildPythonPackage rec {
    pname = "pinecone-client";
    version = "5.0.1";
    pyproject = true;

    disabled = pythonOlder "3.8";

    src = fetchPypi {
      pname = "pinecone_client";
      inherit version;
      hash = "sha256-EcM/9dHDimzmnmn+UywPIvMS+yjXYbsws3Z4FtMYHWQ=";
    };

    pythonRelaxDeps = ["urllib3" "pinecone-plugin-inference"];
    # pythonRemoveDeps = [ "pinecone-plugin-interface" ];

    nativeBuildInputs = [pythonRelaxDepsHook];

    build-system = [
      setuptools
      poetry-core
    ];

    dependencies = [
      dnspython
      loguru
      numpy
      python-dateutil
      pyyaml
      requests
      tqdm
      typing-extensions
      urllib3
      pinecone-plugin-inference
      pinecone-plugin-interface
    ];

    # Tests require network access
    doCheck = false;

    pythonImportsCheck = ["pinecone"];

    meta = with lib; {
      description = "The Pinecone python client";
      homepage = "https://www.pinecone.io/";
      changelog = "https://github.com/pinecone-io/pinecone-python-client/releases/tag/v${version}";
      license = licenses.mit;
      maintainers = with maintainers; [happysalada];
    };
  }
