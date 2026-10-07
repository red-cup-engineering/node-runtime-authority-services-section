import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const storageUrl = process.env.RDF_STORAGE_URL || 'http://localhost:3000';
    const response = await fetch(`${storageUrl}/trigger/validation`, {
      method: 'POST'
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: 'Failed to trigger validation', details: error },
        { status: 500 }
      );
    }
    
    return NextResponse.json({ 
      success: true, 
      message: 'Validation event triggered. Check the Validation Graph in ~10 seconds for results.' 
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to trigger validation', details: String(error) },
      { status: 500 }
    );
  }
}
