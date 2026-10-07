import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const storageUrl = process.env.RDF_STORAGE_URL || 'http://localhost:3000';
    const body = await request.json();
    
    const response = await fetch(`${storageUrl}/triples`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: 'Failed to add triple', details: error },
        { status: 500 }
      );
    }
    
    return NextResponse.json(await response.json());
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to add triple', details: String(error) },
      { status: 500 }
    );
  }
}

export async function PUT(request: NextRequest) {
  try {
    const storageUrl = process.env.RDF_STORAGE_URL || 'http://localhost:3000';
    const body = await request.json();
    
    const response = await fetch(`${storageUrl}/triples`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: 'Failed to upsert triple', details: error },
        { status: 500 }
      );
    }
    
    return NextResponse.json(await response.json());
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to upsert triple', details: String(error) },
      { status: 500 }
    );
  }
}

export async function DELETE(request: NextRequest) {
  try {
    const storageUrl = process.env.RDF_STORAGE_URL || 'http://localhost:3000';
    const body = await request.json();
    
    const response = await fetch(`${storageUrl}/triples`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      const error = await response.json();
      return NextResponse.json(
        { error: 'Failed to delete triple', details: error },
        { status: 500 }
      );
    }
    
    return NextResponse.json(await response.json());
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to delete triple', details: String(error) },
      { status: 500 }
    );
  }
}
