import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const storageUrl = process.env.RDF_STORAGE_URL || 'http://localhost:3000';
    const response = await fetch(`${storageUrl}/trigger/reasoning`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: 'Failed to trigger reasoning', details: error },
        { status: 500 }
      );
    }
    
    return NextResponse.json({ 
      success: true, 
      message: 'Reasoning event triggered. Check the Inference Graph in ~10 seconds for results.' 
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to trigger reasoning', details: String(error) },
      { status: 500 }
    );
  }
}
