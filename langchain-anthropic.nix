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
  ...
}:

buildPythonPackage rec {
  pname = "langchain-anthropic";
  version = "0.2.1";
  pyproject = true;

  src = fetchFromGitHub {
    owner = "langchain-ai";
    repo = "langchain";
    rev = "refs/tags/langchain-anthropic==${version}";
    hash = "sha256-M1gyw0Nmh+aLU9scbuqmK2kPyfwtaFaCfue+T8PLguQ=";
  };

  sourceRoot = "${src.name}/libs/partners/anthropic";

  preConfigure = ''
    substituteInPlace pyproject.toml \
      --replace-fail "^0.7.1" "^0.8.0rc2"
  '';

  build-system = [ poetry-core ];

  dependencies = [
    langchain-core
    anthropic
    tiktoken
    defusedxml
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

  pytestFlagsArray = [ "tests/unit_tests" ];

  disabledTests = [
    # These tests require network access
    "test__get_encoding_model"
    "test_get_token_ids"
    "test_azure_openai_secrets"
    "test_azure_openai_api_key_is_secret_string"
    "test_get_num_tokens_from_messages"
    "test_azure_openai_api_key_masked_when_passed_from_env"
    "test_azure_openai_api_key_masked_when_passed_via_constructor"
    "test_azure_openai_uses_actual_secret_value_from_secretstr"
    "test_azure_serialized_secrets"
    "test_openai_get_num_tokens"
    "test_chat_openai_get_num_tokens"
  ];

  pythonImportsCheck = [ "langchain_anthropic" ];

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