# The table's models and wood

The scanned things on the table under the book, drawn by `web/src/lib/desk/scene.ts`. The matchbox,
match, pencil and mug are built in code (`desk/props.ts`) and are not here.

They are in `public/`, not `src/assets/`, because three.js loads them by URL at run time where Vite
cannot see the reference; the scene prefixes `import.meta.env.BASE_URL`, so they resolve under the
GitHub Pages subpath. They are served from this origin like the fonts, so the build still requests
nothing off-origin.

| File | Source | Author | Licence |
| --- | --- | --- | --- |
| `brass_candleholders.glb` | [Brass Candleholders](https://polyhaven.com/a/brass_candleholders), 1k glTF | Tina | CC0 |
| `seadogs_compass.glb` | [Seadogs Compass](https://polyhaven.com/a/seadogs_compass), 1k glTF | Benny Weimer | CC0 |
| `wood_diff.webp`, `wood_nor.webp` | [Dark Wood](https://polyhaven.com/a/dark_wood): diffuse 2k, normal (GL) 1k | Dimitrios Savva, Rico Cilliers, Dario Barresi | CC0 |

CC0 asks for nothing, so this table is a record rather than an obligation: what to fetch again, and
who made it.

## How they were shrunk

0.92 MB all told, against 15.5 MB as downloaded. The page loads them after the book, never
before it, but a background should still cost little.

- **Models**, with `@gltf-transform/core` and `/functions` 4.5.1, `meshoptimizer` 1.3.0 and
  `sharp` 0.35.5: `prune`, `dedup`, `weld`, `textureCompress` to WebP at 512 px and quality 80,
  then `meshopt` at level `medium`. The scene's loader carries the meshopt decoder for that last
  step; a model compressed some other way will not load.
- **The candleholder** is one of the set's several holders: every other node is disposed before
  the transforms, and so is the primitive carrying the model's own flame, since the scene draws its
  own.
- **The wood**: resized with `sharp` to WebP, the colour at 2048 px and quality 82, the normal map at
  1024 px and quality 85. The scanned roughness map is not used: it made the table a mirror for the
  sun, and one roughness for the whole waxed surface reads better from above.
