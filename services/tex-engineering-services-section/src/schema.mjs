import { schemaFrom } from "@red-cup-engineering/json-schema-services-section/contracts";
const idSchema = { type: "string", minLength: 1 };
const stringSequenceSchema = { type: "array", items: idSchema };
const jsonValueSchema = {};
export const texCommandSchema = {
    $id: "metroplat/tex/command",
    title: "TexCommand",
    description: "A TeX command occurrence read from source text.",
    type: "object",
    required: ["name", "line"],
    additionalProperties: false,
    properties: {
        name: idSchema,
        argument: { type: "string" },
        line: { type: "integer", minimum: 1 },
    },
};
export const texCommandContract = schemaFrom(texCommandSchema);
export const texEnvironmentSchema = {
    $id: "metroplat/tex/environment",
    title: "TexEnvironment",
    description: "A TeX environment occurrence read from source text.",
    type: "object",
    required: ["name", "line"],
    additionalProperties: false,
    properties: {
        name: idSchema,
        title: { type: "string" },
        line: { type: "integer", minimum: 1 },
    },
};
export const texEnvironmentContract = schemaFrom(texEnvironmentSchema);
export const texDependencySchema = {
    $id: "metroplat/tex/dependency",
    title: "TexDependency",
    description: "A textual dependency edge declared by a TeX-family plate.",
    type: "object",
    required: ["kind", "target", "command", "line"],
    additionalProperties: false,
    properties: {
        kind: { enum: ["input", "include", "import", "package", "bibliography", "uses"] },
        target: idSchema,
        command: idSchema,
        line: { type: "integer", minimum: 1 },
    },
};
export const texDependencyContract = schemaFrom(texDependencySchema);
export const texLabelSchema = {
    $id: "metroplat/tex/label",
    title: "TexLabel",
    description: "A stable label declared by a TeX-family plate.",
    type: "object",
    required: ["name", "line"],
    additionalProperties: false,
    properties: {
        name: idSchema,
        line: { type: "integer", minimum: 1 },
    },
};
export const texLabelContract = schemaFrom(texLabelSchema);
export const texReferenceSchema = {
    $id: "metroplat/tex/reference",
    title: "TexReference",
    description: "A reference from one TeX-family plate occurrence to another named label.",
    type: "object",
    required: ["target", "command", "line"],
    additionalProperties: false,
    properties: {
        target: idSchema,
        command: idSchema,
        line: { type: "integer", minimum: 1 },
    },
};
export const texReferenceContract = schemaFrom(texReferenceSchema);
export const texPlateSchema = {
    $id: "metroplat/tex/plate",
    title: "TexPlate",
    description: "A TeX-family file admitted as a textual plate, before any engine or app runtime acts on it.",
    type: "object",
    required: ["kind", "source", "format", "commands", "environments", "dependencies", "labels", "references"],
    additionalProperties: false,
    properties: {
        kind: { const: "metroplat.tex.plate" },
        source: idSchema,
        format: { enum: ["generic-tex", "blueprint-tex", "verso-tex"] },
        commands: { type: "array", items: texCommandSchema },
        environments: { type: "array", items: texEnvironmentSchema },
        dependencies: { type: "array", items: texDependencySchema },
        labels: { type: "array", items: texLabelSchema },
        references: { type: "array", items: texReferenceSchema },
        mediaType: { type: "string" },
    },
};
export const texPlateContract = schemaFrom(texPlateSchema);
