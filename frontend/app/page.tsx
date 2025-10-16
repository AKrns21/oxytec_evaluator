"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import FileUpload from "@/components/FileUpload";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const router = useRouter();
  const [files, setFiles] = useState<File[]>([]);
  const [company, setCompany] = useState("");
  const [contact, setContact] = useState("");
  const [requirements, setRequirements] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (files.length === 0) {
      alert("Please upload at least one document");
      return;
    }

    setIsSubmitting(true);

    try {
      const formData = new FormData();

      // Add files
      files.forEach(file => {
        formData.append("files", file);
      });

      // Add metadata
      const metadata = {
        company,
        contact,
        requirements,
      };
      formData.append("user_metadata", JSON.stringify(metadata));

      // Submit to API
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const response = await fetch(`${apiUrl}/api/sessions/create`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to create session");
      }

      const data = await response.json();

      // Redirect to session page
      router.push(`/session/${data.session_id}`);
    } catch (error) {
      console.error("Error creating session:", error);
      alert("Failed to create feasibility study. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">
          Create Feasibility Study
        </h1>
        <p className="text-muted-foreground">
          Upload your customer inquiry documents and let our AI agents analyze the requirements
          and generate a comprehensive feasibility report.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Document Upload */}
        <Card>
          <CardHeader>
            <CardTitle>Upload Documents</CardTitle>
            <CardDescription>
              Upload technical specifications, VOC analysis, customer requirements, or any relevant documents.
              Supported formats: PDF, Word, Excel, CSV
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload files={files} setFiles={setFiles} />
          </CardContent>
        </Card>

        {/* Customer Information */}
        <Card>
          <CardHeader>
            <CardTitle>Customer Information</CardTitle>
            <CardDescription>
              Provide basic information about the customer and their requirements
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="company">Company Name</Label>
              <Input
                id="company"
                placeholder="ABC Manufacturing GmbH"
                value={company}
                onChange={(e) => setCompany(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact">Contact Person</Label>
              <Input
                id="contact"
                placeholder="john.doe@example.com"
                value={contact}
                onChange={(e) => setContact(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="requirements">Additional Requirements</Label>
              <textarea
                id="requirements"
                className="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Any specific requirements, constraints, or notes..."
                value={requirements}
                onChange={(e) => setRequirements(e.target.value)}
              />
            </div>
          </CardContent>
        </Card>

        {/* Submit Button */}
        <div className="flex justify-end">
          <Button
            type="submit"
            size="lg"
            disabled={isSubmitting || files.length === 0}
            className="min-w-[200px]"
          >
            {isSubmitting ? (
              <>
                <svg
                  className="animate-spin -ml-1 mr-3 h-5 w-5 text-white"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  ></path>
                </svg>
                Creating Study...
              </>
            ) : (
              "Start Analysis"
            )}
          </Button>
        </div>
      </form>

      {/* Info Box */}
      <Card className="mt-8 bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <svg
                className="h-6 w-6 text-blue-600"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <div className="flex-1">
              <h3 className="text-sm font-medium text-blue-900">
                What happens next?
              </h3>
              <p className="mt-2 text-sm text-blue-700">
                Our AI system will analyze your documents in multiple parallel stages:
                extracting technical facts, creating specialized analysis agents, evaluating
                products and solutions, assessing risks, and generating a comprehensive
                feasibility report. This typically takes 40-70 seconds.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
