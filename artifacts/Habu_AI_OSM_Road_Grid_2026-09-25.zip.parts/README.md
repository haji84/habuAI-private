# Habu AI OSM Road Grid archive parts

Original file: `Habu_AI_OSM_Road_Grid_2026-09-25.zip`  
Parts: 33 (`part_000.b64` through `part_032.b64`)  
Original SHA-256: `f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17`

Restore:

```bash
cat part_*.b64 | base64 --decode > Habu_AI_OSM_Road_Grid_2026-09-25.zip
echo "f4d7a9925c98830a0b6918f756abe49b2b0f2eb935fc49c2d4eb42a732884c17  Habu_AI_OSM_Road_Grid_2026-09-25.zip" | sha256sum --check
unzip -t Habu_AI_OSM_Road_Grid_2026-09-25.zip
```

Do not use the restored archive unless both checks pass.
