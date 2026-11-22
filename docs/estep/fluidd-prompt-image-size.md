# Fluidd: show a single picture big (file `src/components/common/ActionCommandPromptDialog.vue`)

Why: in the built Fluidd the style is `.prompt-image { flex: 240px; width: 100%; min-width: 0; max-width: 300px; height: auto }`,
so every picture is at most 300 px wide, also when the window has one picture only. The window itself is allowed 980 px
(`max-width` 980 when it has a picture). The e-step pictures are 1600 x 960 with text, they need the full window width.

Change (the image item is rendered as `<v-col class="prompt-images">` with one `<img class="prompt-image">` per name in
`item.names`, see the built bundle of Fluidd 1.38.0 + our patches):

1. Template: add a class on the `v-col` of the image item, true when the item has exactly one picture:

```vue
<v-col
  v-else-if="item.type === 'image'"
  class="prompt-images"
  :class="{ 'prompt-images--single': item.names.length === 1 }"
>
```

2. Style, after the existing `.prompt-image` rule:

```scss
.prompt-images--single .prompt-image {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}
```

Result: one picture fills the window (about 930 px on a desktop, the full width on a phone), at most 70 percent of the window
height; two to four pictures stay at 300 px as before (the three setter pictures are not changed). It adapts to any browser size
because it only uses percentages and vh.

Pictures: copy `images/svg/*.svg` to `public/img/wm/` (names estep-prepare, estep-ruler, estep-zero, estep-measure). The SVG files
hold the picture as an embedded image (JPEG or PNG), so they show the same on every screen. Rebuild Fluidd as for the other patches.

## Applied on the main RPi4 (built Fluidd, no rebuild) - 2026-11-22
Pure CSS, no JS template change (a one-picture window is found with `:has`):

    .prompt-images[data-v-89e1219d]:has(>.prompt-image:only-child) .prompt-image[data-v-89e1219d]{max-width:100%;max-height:72vh;object-fit:contain}

appended to `fluidd/assets/index-*.css` (the file that holds `.prompt-image[data-v-89e1219d]`), and in `fluidd/assets/index-*.js`
the window width `e.hasImage?980:640` became `e.hasImage?1200:640`. Backups: `config/backup/fluidd-index.*.wm-before-estep-img-<stamp>`.
The hashes (data-v, file names) change with every Fluidd build, find them again with grep. Reload the page with a hard refresh.
