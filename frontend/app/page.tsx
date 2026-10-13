import ImpurityInspector from "@/components/ImpurityInspector";

export default function Home() {
  return (
    <main className="container">
      <header className="header">
        <h1>Inspeção de Impurezas em Metais Raros</h1>
        <p>Classificador Haar Cascade · OpenCV · FastAPI</p>
      </header>
      <ImpurityInspector />
    </main>
  );
}
