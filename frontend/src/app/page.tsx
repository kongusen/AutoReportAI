import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ArrowRight, Zap } from 'lucide-react'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div>
      {/* Header */}
      <header className="container flex items-center justify-between py-6">
        <div className="text-2xl font-bold tracking-tight">AutoReport AI</div>
        <nav className="flex gap-6 text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition-colors">Features</a>
          <a href="#about" className="hover:text-foreground transition-colors">About</a>
          <Link href="/login" className="hover:text-foreground transition-colors">Sign In</Link>
        </nav>
      </header>

      {/* Hero Section */}
      <section className="py-24 px-4">
        <div className="container text-center">
          <Badge variant="secondary" className="mb-6">
            <Zap className="h-3 w-3 mr-1" />
            AI-Powered Reporting
          </Badge>
          <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
            <span className="text-gradient">Intelligent</span> Report<br /> Generation
          </h1>
          <p className="text-lg text-muted-foreground mb-8">
            Create insightful reports effortlessly with our AI-driven platform.
          </p>
          <Button size="lg">
            Get Started
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-24 px-4 bg-muted">
        <div className="container">
          <h2 className="text-3xl font-bold text-center mb-12">Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <Card>
              <CardHeader>
                <CardTitle>Automated Insights</CardTitle>
                <CardDescription>Get real-time insights generated automatically.</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Utilize AI to analyze data and generate reports without manual input.</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Customizable Templates</CardTitle>
                <CardDescription>Choose from a variety of templates to suit your needs.</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Personalize your reports with our easy-to-use template editor.</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Collaboration Tools</CardTitle>
                <CardDescription>Work together with your team seamlessly.</CardDescription>
              </CardHeader>
              <CardContent>
                <p>Share reports and collaborate in real-time with your colleagues.</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 bg-background">
        <div className="container text-center">
          <p className="text-sm text-muted-foreground">© 2023 AutoReport AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}