import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { name: string } }
) {
  try {
    const storageUrl = process.env.RDF_STORAGE_URL || 'http://localhost:3000';
    const { name } = params;
    
    const response = await fetch(`${storageUrl}/graphs/${name}`);
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch graph', details: await response.text() },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error', details: String(error) },
      { status: 500 }
    );
  }
}
