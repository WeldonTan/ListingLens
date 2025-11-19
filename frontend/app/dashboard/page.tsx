"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/lib/api"

interface Listing {
  id: number
  url: string
  listing_title: string
  price: number
  state: string
  area: string
}

export default function DashboardPage() {
  const [listings, setListings] = useState<Listing[]>([])

  useEffect(() => {
    const fetchListings = async () => {
      try {
        const response = await api.get("/listings/")
        setListings(response.data)
      } catch (error) {
        console.error("Failed to fetch listings", error)
      }
    }
    fetchListings()
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Properties</h1>
        <Link href="/dashboard/scrape">
          <Button>Add New Listing</Button>
        </Link>
      </div>
      
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {listings.map((listing) => (
          <Card key={listing.id}>
            <CardHeader>
              <CardTitle className="truncate">{listing.listing_title || "Untitled Listing"}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <p className="text-2xl font-bold">
                  {listing.price ? `RM ${listing.price.toLocaleString()}` : "N/A"}
                </p>
                <div className="text-sm text-gray-500">
                  <p>{listing.area}, {listing.state}</p>
                  <a href={listing.url} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline block truncate">
                    View Original
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
