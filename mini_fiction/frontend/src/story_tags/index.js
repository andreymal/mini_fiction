/* eslint-disable import/no-unresolved */
import ReactDOM from 'react-dom';
import TagComponent from './component';

export default (node) => {
  ReactDOM.render(ReactDOM.createElement(TagComponent), node);
};
