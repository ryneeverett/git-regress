with import <nixpkgs> {};

pkgs.mkShell {
  buildInputs = [
    pkgs.git
    pkgs.python3Packages.pytest
    (pkgs.python3Packages.scripttest.overrideAttrs (oldAttrs: {
      src = pkgs.fetchgit {
        url = "https://github.com/ryneeverett/scripttest.git";
        rev = "52b5ea0b5c0d2cda593931827d94ba484ed26f32";
        sha256 = "1waakcl0zxr13mx2haic7yn8z1nvpwaivy9dsf5xh7irsh2yx66r";
      };
    }))
  ];
}
