import {useEffect, useState} from "react";
import {getBackendInfo} from "./tripsService.js";

// Shows which frontend and backend versions are running (Git tag -> ECR image tag -> ECS task).
const frontendVersion = import.meta.env.VITE_APP_VERSION || "dev";

export default function VersionInfo() {
    const [backend, setBackend] = useState("…");

    useEffect(() => {
        getBackendInfo()
            .then((info) => setBackend(info?.app?.version || "unbekannt"))
            .catch(() => setBackend("nicht erreichbar"));
    }, []);

    return (
        <p className="small text-muted mb-1" data-testid="versions">
            Frontend <code>{frontendVersion}</code> · Backend <code>{backend}</code>
        </p>
    );
}
