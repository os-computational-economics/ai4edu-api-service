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
  pdm,
  pytest-asyncio,
  pytestCheckHook,
  pytest-mock,
  pytest-socket,
  requests-mock,
  responses,
  syrupy,
  toml,
  pdm-backend,
  pinecone-client,
  ...
}:
buildPythonPackage rec {
  pname = "langchain-pinecone";
  version = "v0.2.4rc1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "langchain-ai";
    repo = "langchain-pinecone";
    rev = "refs/tags/libs/pinecone/${version}";
    hash = "sha256-/AFuH7fwAn9vkJrpG/AD6Cm0YWW1uOEQNmnq18eHliQ=";
  };

  sourceRoot = "${src.name}/libs/pinecone";

  build-system = [poetry-core];

  dependencies = [
    langchain-core
    aiohttp
    pdm
    pdm-backend
    pinecone-client
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

  pythonRelaxDeps = ["aiohttp" "numpy"];
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
