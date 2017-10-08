const util = require('util');
const exec = util.promisify(require('child_process').exec);

async function gm11() {
  const inputs = [223.3, 227.3, 230.5, 238.1];
  const { stdout } = await exec(`python gm11.py ${JSON.stringify(inputs)}`);
  const result = stdout.match(/Forcated next moment value is (\S+)/)[1];
  console.log(result);
}

gm11();