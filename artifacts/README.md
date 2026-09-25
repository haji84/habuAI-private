# Artifacts

大きな復元用成果物は分割base64で保存する場合がある。

復元例:

```bash
cat artifacts/FILE.parts/part_* | base64 --decode > FILE
sha256sum FILE
```

復元後のSHA-256は同ディレクトリの`SHA256SUMS`と一致しなければならない。

