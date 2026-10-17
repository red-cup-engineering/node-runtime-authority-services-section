/**
 * Code owns the executable declaration of the source-owned content-space
 * effects. Data owns its input/output types, Networking projects the same
 * operations to MCP, and Systems binds the original custody effect.
 */
import { defineType } from "@red-cup-engineering/signcell/type-system";
import {
  contentSpacePutInputSchema,
  contentSpaceLinkInputSchema,
  contentSpacePublicationSchema,
} from "@red-cup-engineering/computer-data-engineering-services-section/content-space-operation-schemas";
import { declareCapabilityOperation } from "./typed-operation.mjs";

const establish = (id,schema) => {
  const result=defineType({
    id:"content-space/"+id+"/v1",
    name:"ContentSpace"+id,
    description:"An admitted content-space operation input or result",
    parents:[],schema,
  });
  if(!result.ok)
    throw new TypeError("content-space type unavailable: "+result.refusal.message);
  return result.value;
};
const output=establish("Publication",contentSpacePublicationSchema);

export const contentSpaceCapabilityOperations = Object.freeze([
  ["content-space-put-path",contentSpacePutInputSchema,
    "Publish exact bytes into an authorized named NI tree"],
  ["content-space-link-path",contentSpaceLinkInputSchema,
    "Link an independently admitted NI into a named tree without copying bytes"],
].map(([id,schema,description])=>{
  const result=declareCapabilityOperation({
    id,description,domain:establish(id,schema),codomain:output,
    effects:["content-space.publish"],capability:id,
  });
  if(!result.ok)
    throw new TypeError("content-space capability unavailable: "+result.refusal.message);
  return result.value;
}));
