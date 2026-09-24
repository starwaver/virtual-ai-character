import { defineConfig, presetWind3, transformerVariantGroup } from 'unocss'

export default defineConfig({
  presets: [presetWind3()],
  transformers: [transformerVariantGroup()],
  theme: {
    colors: {
      primary: {
        100: '#ffe7ad',
        200: '#f1cf85',
        300: '#d9ac53',
        400: '#b98329',
        500: '#8a5b1d',
        800: '#412f17',
        900: '#281e13',
      },
    },
  },
  content: {
    pipeline: {
      include: [
        'src/**/*.{vue,ts}',
        'index.html',
        '../../packages/ui/src/**/*.{vue,ts}',
      ],
    },
  },
})
