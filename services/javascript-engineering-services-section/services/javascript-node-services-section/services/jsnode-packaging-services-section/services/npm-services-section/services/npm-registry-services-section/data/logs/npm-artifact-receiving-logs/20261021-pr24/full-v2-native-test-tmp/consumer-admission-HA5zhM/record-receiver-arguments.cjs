const fs = require("node:fs"), path = require("node:path");
fs.writeFileSync(process.argv[2], JSON.stringify(process.argv.slice(3)));
const project = process.argv[process.argv.indexOf("--dir") + 1];
const modules = path.join(project, "node_modules");
fs.mkdirSync(modules);
fs.writeFileSync(path.join(modules, ".modules.yaml"), "layoutVersion: 5\n");
for (const [name, version] of Object.entries(JSON.parse(fs.readFileSync(path.join(project, "package.json"))).dependencies || {})) {
  const dependency = path.join(modules, name); fs.mkdirSync(dependency, { recursive: true });
  fs.writeFileSync(path.join(dependency, "package.json"), JSON.stringify({ name, version }));
}
