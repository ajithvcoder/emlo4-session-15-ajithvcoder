import SimpleFileUpload from '../components/SimpleFileUpload';

export default function Home() {
  return (
    <main className="container mx-auto p-4">
      <header className="text-center my-4">
        <h1 className="text-2xl font-bold">TSAI - EMLO V4</h1>
        <p className="text-gray-600">Cat and Dog Classifier powered by FastAPI, Model Server, Kubernetes, and Redis Caching</p>
      </header>
      <SimpleFileUpload />
    </main>
  );
}