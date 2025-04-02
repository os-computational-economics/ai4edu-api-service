{
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  # build-system
  poetry-core,
  # dependencies
  langchain-core,
  anthropic,
  tiktoken,
  defusedxml,
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
  pdm,
  pdm-backend,
  ...
}:
buildPythonPackage rec {
  pname = "langchain-anthropic";
  version = "0.3.10";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "langchain-ai";
    repo = "langchain";
    rev = "refs/tags/langchain-anthropic==${version}";
    hash = "sha256-8R5qMaMD05lIpf3oDWV8BJbXz3Ij4OpOie3Joxp9YOo=";
  };

  sourceRoot = "${src.name}/libs/partners/anthropic";

  # preConfigure = ''
  #   substituteInPlace pyproject.toml \
  #     --replace-fail "^0.7.1" "^0.8.0rc2"
  # '';

  build-system = [poetry-core];

  dependencies = [
    langchain-core
    anthropic
    tiktoken
    defusedxml
    pdm
    pdm-backend
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
  ];

  pythonImportsCheck = ["langchain_anthropic"];

  passthru = {
    inherit (langchain-core) updateScript;
  };

  meta = {
    changelog = "https://github.com/langchain-ai/langchain/releases/tag/langchain-anthropic==${version}";
    description = "Integration package connecting Anthropic and LangChain";
    homepage = "https://github.com/langchain-ai/langchain/tree/master/libs/partners/anthropic";
    license = lib.licenses.mit;
    # maintainers = with lib.maintainers; [ natsukium ];
  };
}
