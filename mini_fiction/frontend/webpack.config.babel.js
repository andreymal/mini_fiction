import webpack from 'webpack';
import path from 'path';

const ENV = process.env.NODE_ENV || 'development';


const reactAliases = {
  react: 'preact-compat',
  'react-dom': 'preact-compat',
};


module.exports = {
  mode: ENV,
  context: path.resolve(__dirname, 'src'),
  entry: {
    story: './story.js',
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
    ],
  },
  plugins: ([
    new webpack.NoEmitOnErrorsPlugin(),
    new webpack.DefinePlugin({
      'process.env.NODE_ENV': JSON.stringify(ENV),
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
