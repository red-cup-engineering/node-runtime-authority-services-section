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
  contentSpaceLinkBatchInputSchema,
  contentSpaceBatchPublicationSchema,
  contentSpaceWalkInputSchema,
  contentSpaceWalkOutputSchema,
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
const publication=establish("Publication",contentSpacePublicationSchema);
const batchPublication=establish("BatchPublication",contentSpaceBatchPublicationSchema);
const snapshotWalk=establish("Walk",contentSpaceWalkOutputSchema);

/** All operations use the ORIGINAL Code type/effect machinery and Networking projection. */
export const contentSpaceCapabilityOperations = Object.freeze([
  ["content-space-put-path",contentSpacePutInputSchema,publication,
    "Publish exact bytes into an authorized named NI tree","content-space.publish"],
  ["content-space-link-path",contentSpaceLinkInputSchema,publication,
    "Link an independently admitted NI into a named tree without copying bytes","content-space.publish"],
  ["content-space-link-batch",contentSpaceLinkBatchInputSchema,batchPublication,
    "Publish a bounded collection of held NI links in one compare-and-publish","content-space.publish"],
  ["content-space-walk",contentSpaceWalkInputSchema,snapshotWalk,
    "Read a bounded, independently authorized immutable NI Merkle territory","content-space.read"],
].map(([id,schema,codomain,description,effect])=>{
  const result=declareCapabilityOperation({
    id,description,domain:establish(id,schema),codomain,
    effects:[effect],capability:id,
  });
  if(!result.ok)
    throw new TypeError("content-space capability unavailable: "+result.refusal.message);
  return result.value;
}));
