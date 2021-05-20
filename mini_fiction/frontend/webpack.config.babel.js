import path from 'path';
import AssetsManifestPlugin from 'webpack-assets-manifest';
import MiniCssExtractPlugin from 'mini-css-extract-plugin';
import TerserPlugin from 'terser-webpack-plugin';
import { CleanWebpackPlugin } from 'clean-webpack-plugin';

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
  react: 'preact/compat',
  'react-dom': 'preact/compat',
};

const postCSSOptions = {
  plugins: [
    postCSSAutoPrefixer(),
    postCSSMixins(),
    postCSSNesting(),
    postCSSCustomProperties({
      preserve: false,
      warnings: true,
    }),
    postCSSNano({
      preset: ['default', {
        discardComments: !isDev,
        normalizeWhitespace: !isDev,
      }],
    }),
  ],
};

const cssLoaderOptions = {
  modules: false,
  importLoaders: 1,
  url: true,
};

const extractLoaderOptions = {
  publicPath: './',
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
    publicPath: '/static/build/',
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
          { loader: 'postcss-loader', options: { postcssOptions: postCSSOptions } },
        ],
      },
      {
        test: /images\/markitup/,
        type: 'asset/source',
      },
      {
        test: /\.(png|jpg|gif|eot|ttf|woff|woff2)$/,
        type: 'asset',
        parser: {
          dataUrlCondition: {
            maxSize: 8192,
          },
        },
      },
    ],
  },
  optimization: {
    minimize: !isDev,
    minimizer: [
      new TerserPlugin({
        extractComments: false,
      }),
    ],
    splitChunks: {
      cacheGroups: {
        vendor: {
          test: /[\\/](node_modules|legacy\/lib)[\\/]/,
          name: 'vendor',
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
    new CleanWebpackPlugin(),
    new AssetsManifestPlugin({
      output: 'manifest.json',
      integrity: true,
      integrityHashes: ['sha256'],
      customize: (_, original) => original,
    }),
  ],

  stats: { colors: true },

  node: {
    global: true,
    __filename: false,
    __dirname: false,
  },

  devtool: 'source-map',
};
