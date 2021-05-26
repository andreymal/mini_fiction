const getKey = (prefix, key) => {
  const k = key.slice(prefix.length);
  return k.charAt(0).toLowerCase() + k.slice(1);
};

export const filterParams = (prefix, obj) => Object.keys(obj)
  .filter((k) => k.startsWith(prefix))
  .reduce((acc, k) => {
    acc[getKey(prefix, k)] = obj[k];
    return acc;
  }, {});

export const capitalize = (v) => v.charAt(0).toUpperCase() + v.slice(1);

export const normalize = (v) => v.toLowerCase().trim();
