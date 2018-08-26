import path from 'path';
import AssetsManifestPlugin from 'webpack-assets-manifest';
import MiniCssExtractPlugin from 'mini-css-extract-plugin';
import CleanWebpackPlugin from 'clean-webpack-plugin';
import HashedModuleIdsPlugin from 'webpack/lib/HashedModuleIdsPlugin';

import postCSSAutoPrefixer from 'autoprefixer';
import postCSSNesting from 'postcss-nesting';
import postCSSCustomProperties from 'postcss-custom-properties';
import postCSSMixins from 'postcss-mixins';
import postCSSNano from 'cssnano';

const ENV = process.env.NODE_ENV || 'development';
const isDev = ENV !== 'production';

const outputPath = path.resolve(__dirname, 'build');
const outputName = `[name].${isDev ? 'dev' : '[contenthash]'}`;


const reactAliases = {
  react: 'preact-compat',
  'react-dom': 'preact-compat',
};

const postCSSLoaderOptions = {
  plugins: () => [
    postCSSAutoPrefixer({
      browsers: [
        'last 3 versions',
        '> 1%',
        'IE 11',
      ],
    }),
    postCSSMixins(),
    postCSSNesting(),
    postCSSCustomProperties({
      preserve: false,
      warnings: true,
    }),
  ].concat(isDev ? [] : [postCSSNano({ preset: 'advanced' })]),
};

const cssLoaderOptions = {
  modules: false,
  importLoaders: 1,
  minimize: !isDev,
  url: true,
};

const extractLoaderOptions = {
  publicPath: './',
};

const urlLoaderOptions = {
  fallback: 'file-loader',
  limit: 8192,
  name: `${outputName}.[ext]`,
};

module.exports = {
  mode: ENV,
  context: path.resolve(__dirname, 'src'),
  entry: {
    story: ['./story.js', './story.css'],
    index: ['./index.js', './index.css'],
  },

  output: {
    path: outputPath,
    publicPath: '/',
    filename: `${outputName}.js`,
  },

  resolve: {
    extensions: ['.jsx', '.js', '.json', 'png', '.jpg', '.gif', '.svg', '.eot', '.ttf', '.woff', '.woff2'],
    modules: [
      path.resolve(__dirname, 'src'),
      path.resolve(__dirname, 'node_modules'),
      'node_modules',
    ],
    alias: reactAliases,
  },

  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: path.resolve(__dirname, 'src'),
        enforce: 'pre',
        use: 'source-map-loader',
      },
      {
        test: /\.jsx?$/,
        exclude: /node_modules/,
        use: [
          { loader: 'babel-loader' },
          { loader: 'webpack-remove-block-loader', options: { active: !isDev } },
        ],
      },
      {
        test: /\.css$/,
        use: [
          { loader: MiniCssExtractPlugin.loader, options: extractLoaderOptions },
          { loader: 'css-loader', options: cssLoaderOptions },
          { loader: 'postcss-loader', options: postCSSLoaderOptions },
        ],
      },
      {
        test: /\.(png|jpg|gif|svg|eot|ttf|woff|woff2)$/,
        use: [
          { loader: 'url-loader', options: urlLoaderOptions },
        ],
      },
    ],
  },
  optimization: {
    minimize: !isDev,
    splitChunks: {
      cacheGroups: {
        vendor: {
          test: /[\\/](node_modules|legacy\/lib)[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
      },
    },
  },
  plugins: [
    new MiniCssExtractPlugin({
      filename: `${outputName}.css`,
      chunkFilename: '[id].css',
    }),
    new CleanWebpackPlugin(outputPath, { watch: true, beforeEmit: true }),
    new AssetsManifestPlugin({
      output: 'manifest.json',
      integrity: true,
      integrityHashes: ['sha384'],
      customize: (_, original) => original,
    }),
  ].concat(isDev ? [] : new HashedModuleIdsPlugin()),

  stats: { colors: true },

  node: {
    global: true,
    process: false,
    Buffer: false,
    __filename: false,
    __dirname: false,
    setImmediate: false,
  },

  devtool: 'source-map',
};
