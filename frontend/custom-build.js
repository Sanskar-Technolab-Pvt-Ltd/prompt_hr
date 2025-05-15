
const fs = require('fs-extra');
const path = require('path');
const { execSync } = require('child_process');

const lmsAppPath = path.resolve(__dirname, '../../lms/frontend');
const overrideSrcPath = path.resolve(__dirname, 'src');
const overrideFilesPath = path.resolve(__dirname, './src_override');

console.log('Starting  : Copying original src.');
fs.copySync(path.join(lmsAppPath, 'src'), overrideSrcPath);
console.log('Completed : Copying original src.');

console.log('Starting  : Overriding src.');
fs.copySync(overrideFilesPath, overrideSrcPath);
console.log('Completed : Overriding src.');

execSync('yarn install', { stdio: 'inherit' });