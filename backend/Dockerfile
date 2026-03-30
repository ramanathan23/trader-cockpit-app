# ── Stage 1: restore ─────────────────────────────────────────────────────────
# Copy only project files first so the restore layer is cached independently
# of source changes.
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS restore
WORKDIR /src

COPY TraderCockpit.sln .
COPY src/TraderCockpit.Infrastructure/TraderCockpit.Infrastructure.csproj src/TraderCockpit.Infrastructure/
COPY src/TraderCockpit.MarketData/TraderCockpit.MarketData.csproj    src/TraderCockpit.MarketData/
COPY src/TraderCockpit.Api/TraderCockpit.Api.csproj                  src/TraderCockpit.Api/

RUN dotnet restore

# ── Stage 2: publish ──────────────────────────────────────────────────────────
FROM restore AS publish
COPY . .

RUN dotnet publish src/TraderCockpit.Api/TraderCockpit.Api.csproj \
        --configuration Release \
        --no-restore \
        --output /app/publish

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
WORKDIR /app

# .NET 8+ containers default to port 8080 (HTTP) — no ASPNETCORE_URLS override needed.
EXPOSE 8080

COPY --from=publish /app/publish .

ENTRYPOINT ["dotnet", "TraderCockpit.Api.dll"]
