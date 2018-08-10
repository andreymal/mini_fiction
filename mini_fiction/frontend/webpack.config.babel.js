import path from 'path';
import webpack from 'webpack';
import MiniCssExtractPlugin from 'mini-css-extract-plugin';

import postCSSAutoPrefixer from 'autoprefixer';
import postCSSNesting from 'postcss-nesting';
import postCSSCustomProperties from 'postcss-custom-properties';
import postCSSMixins from 'postcss-mixins';
import postCSSNano from 'cssnano';

const ENV = process.env.NODE_ENV || 'development';
const isDev = ENV !== 'production';


const reactAliases = {
  react: 'preact-compat',
  'react-dom': 'preact-compat',
};

const postCSSLoaderOptions = {
  sourceMap: isDev,
  plugins: () => [
    postCSSAutoPrefixer({ browsers: ['last 2 versions'] }),
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
  sourceMap: isDev,
  importLoaders: 1,
  minimize: !isDev,
};

module.exports = {
  mode: ENV,
  context: path.resolve(__dirname, 'src'),
  entry: {
    story: ['./story.js', './story.css'],
  },

  output: {
    path: path.resolve(__dirname, 'build'),
    publicPath: '/',
    filename: '[name].bundle.js',
  },

  resolve: {
    extensions: ['.jsx', '.js', '.json'],
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
        use: 'babel-loader',
      },
      {
        test: /\.css$/,
        use: [
          { loader: MiniCssExtractPlugin.loader },
          { loader: 'css-loader', options: cssLoaderOptions },
          { loader: 'postcss-loader', options: postCSSLoaderOptions },
        ],
      },
    ],
  },
  plugins: ([
    new MiniCssExtractPlugin({
      filename: '[name].css',
      chunkFilename: '[id].css',
    }),
  ]),

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
