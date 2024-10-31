{
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  # build-system
  poetry-core,
  # dependencies
  langchain-core,
  aiohttp,
  # tests
  freezegun,
  langchain-standard-tests,
  lark,
  pandas,
  pytest-asyncio,
  pytestCheckHook,
  pytest-mock,
  pytest-socket,
  requests-mock,
  responses,
  syrupy,
  toml,
  pkgs,
  ...
}:
buildPythonPackage rec {
  pname = "langchain-pinecone";
  version = "0.2.0";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "langchain-ai";
    repo = "langchain";
    rev = "refs/tags/langchain-anthropic==${version}";
    hash = "sha256-M1gyw0Nmh+aLU9scbuqmK2kPyfwtaFaCfue+T8PLguQ=";
  };

  sourceRoot = "${src.name}/libs/partners/pinecone";

  build-system = [poetry-core];

  dependencies = [
    langchain-core
    aiohttp
    (pkgs.callPackage ./pinecone.nix pkgs.python312Packages)
  ];

  nativeCheckInputs = [
    freezegun
    langchain-standard-tests
    lark
    pandas
    pytest-asyncio
    pytestCheckHook
    pytest-mock
    pytest-socket
    requests-mock
    responses
    syrupy
    toml
  ];

  pytestFlagsArray = ["tests/unit_tests"];

  disabledTests = [
    # These tests require network access
    "test_default_config"
    "test_default_config_with_api_key"
    "test_custom_config"
  ];

  pythonRelaxDeps = ["aiohttp"];
  pythonImportsCheck = ["langchain_pinecone"];

  passthru = {
    inherit (langchain-core) updateScript;
  };

  meta = {
    changelog = "https://github.com/langchain-ai/langchain/releases/tag/langchain-pinecone==${version}";
    description = "Integration package connecting Pinecone and LangChain";
    homepage = "https://github.com/langchain-ai/langchain/tree/master/libs/partners/pinecone";
    license = lib.licenses.mit;
    # maintainers = with lib.maintainers; [ natsukium ];
  };
}
