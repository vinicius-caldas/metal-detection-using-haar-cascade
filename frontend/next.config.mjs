/** @type {import('next').NextConfig} */
const nextConfig = {
  // Gera um servidor Node mínimo e autocontido -> imagem Docker enxuta.
  output: "standalone",
  reactStrictMode: true,
};

export default nextConfig;
