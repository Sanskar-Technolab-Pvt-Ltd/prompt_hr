import resolveConfig from 'tailwindcss/resolveConfig'
// Use require for CommonJS modules
const tailwindConfig = require('../../tailwind.config.js')

export const config = resolveConfig(tailwindConfig)
export const theme = config.theme