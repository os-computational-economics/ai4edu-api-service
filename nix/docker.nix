{ pkgs, app, py }:
pkgs.dockerTools.buildImage {
  name = "ai4edu-api-server";
  tag = "latest";
  copyToRoot = pkgs.buildEnv {
    name = "ai4edu-api-server";
    paths = [ app py ];
    pathsToLink = [ "/bin" ];
  };
  config = {
    Cmd = [ "uvicorn" "main:app" "--host" "0.0.0.0" "--port" "5000" "--proxy-headers"];
    WorkingDir = "${app}";
  };
}