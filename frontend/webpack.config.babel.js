import path from 'path';
import zlib from 'zlib';
import AssetsManifestPlugin from 'webpack-assets-manifest';
import MiniCssExtractPlugin from 'mini-css-extract-plugin';
import TerserPlugin from 'terser-webpack-plugin';
import { CleanWebpackPlugin } from 'clean-webpack-plugin';
import CompressionPlugin from 'compression-webpack-plugin';

import postcss from 'postcss';
import postCSSAutoPrefixer from 'autoprefixer';
import postCSSGlobalData from '@csstools/postcss-global-data';
import postCSSNesting from 'postcss-nesting';
import postCSSMixins from 'postcss-mixins';
import postCSSNano from 'cssnano';
import postCSSCustomProperties from 'postcss-custom-properties';
import postCSSMoveProps from 'postcss-move-props-to-bg-image-query';

const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');

const ENV = process.env.NODE_ENV || 'development';
const isDev = ENV !== 'production';

const outputPath = path.resolve(__dirname, '..', 'mini_fiction', 'static', 'build');
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
    postCSSMoveProps({
      computeCustomProps: root => postcss([
        postCSSGlobalData({
          files: [path.resolve(__dirname, 'src', 'css', 'variables.css')],
        }),
        postCSSCustomProperties({preserve: false}),
      ]).process(root),
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

const defaultPlugins = [
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
];

const devPlugins = [
  new BundleAnalyzerPlugin({
    analyzerMode: 'static',
    openAnalyzer: false,
  }),
];

const productionPlugins = [
  new CompressionPlugin({
    filename: '[path][base].gz',
    algorithm: 'gzip',
    exclude: /.map$/,
  }),
  new CompressionPlugin({
    filename: '[path][base].br',
    algorithm: 'brotliCompress',
    exclude: /.map$/,
    compressionOptions: {
      params: {
        [zlib.constants.BROTLI_PARAM_QUALITY]: 19,
      },
    },
  }),
];

module.exports = {
  mode: ENV,
  context: path.resolve(__dirname, 'src'),
  entry: {
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
          {
            loader: 'webpack-remove-block-loader',
            options: { active: !isDev },
          },
        ],
      },
      {
        test: /\.css$/,
        use: [
          {
            loader: MiniCssExtractPlugin.loader,
            options: extractLoaderOptions,
          },
          {
            loader: 'css-loader',
            options: cssLoaderOptions,
          },
          {
            loader: 'postcss-loader',
            options: { postcssOptions: postCSSOptions },
          },
        ],
      },
      {
        test: /images\/markitup/,
        type: 'asset/source',
      },
      {
        test: /images\/assets\/.*\.svg(\?.*)?$/, // match img.svg and img.svg?param=value
        use: [
          'svg-url-loader', // or file-loader or svg-url-loader
          'svg-transform-loader',
        ],
        type: 'javascript/auto', // https://github.com/bhovhannes/svg-url-loader/issues/524
      },
      {
        test: /\.(png|webp|jpg|gif|eot|ttf|woff|woff2)$/,
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
  },
  plugins: [...defaultPlugins, ...(isDev ? devPlugins : productionPlugins)],

  stats: { colors: true },

  node: {
    global: true,
    __filename: false,
    __dirname: false,
  },

  devtool: 'source-map',
};
