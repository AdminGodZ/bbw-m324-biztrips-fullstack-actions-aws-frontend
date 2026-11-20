import {useEffect, useState} from "react";
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome";
import {faUser, faUpload} from "@fortawesome/free-solid-svg-icons";
import {employeePhotoUrl, getEmployees, uploadEmployeePhoto} from "./tripsService.js";

// RefCard05: employee photos are stored in Amazon S3 by the backend (never public in the bucket).
export default function Employees() {
    const [employees, setEmployees] = useState([]);
    const [error, setError] = useState("");

    useEffect(() => {
        getEmployees()
            .then(setEmployees)
            .catch(() => setError("Mitarbeitende konnten nicht geladen werden."));
    }, []);

    return (
        <section className="my-4">
            <div className="d-flex align-items-center justify-content-between mb-3">
                <h4 className="mb-0">Mitarbeitende</h4>
                <span className="badge text-bg-secondary">Fotos in Amazon S3</span>
            </div>
            {error && <p className="alert alert-warning">{error}</p>}
            <div className="row row-cols-2 row-cols-md-3 row-cols-lg-5 g-3">
                {employees.map((employee) => <Employee key={employee.id} employee={employee}/>)}
            </div>
        </section>
    );
}

function Employee({employee}) {
    const [hasPhoto, setHasPhoto] = useState(Boolean(employee.profilePictureFilename));
    const [version, setVersion] = useState(employee.profilePictureFilename || "");
    const [status, setStatus] = useState("");
    const inputId = `photo-${employee.id}`;

    async function onUpload(event) {
        const file = event.target.files?.[0];
        if (!file) return;
        setStatus("Lade hoch …");
        try {
            await uploadEmployeePhoto(employee.id, file);
            setHasPhoto(true);
            setVersion(String(Date.now()));
            setStatus("");
        } catch (e) {
            setStatus(e.message);
        } finally {
            event.target.value = "";
        }
    }

    return (
        <div className="col">
            <div className="card h-100 shadow-sm">
                {hasPhoto ? (
                    <img src={employeePhotoUrl(employee.id, version)} alt={`Foto von ${employee.name}`}
                         className="card-img-top" style={{height: "140px", objectFit: "cover"}}
                         onError={() => setHasPhoto(false)}/>
                ) : (
                    <div className="d-flex align-items-center justify-content-center bg-light text-secondary"
                         style={{height: "140px"}} aria-label={`Kein Foto von ${employee.name}`}>
                        <FontAwesomeIcon icon={faUser} size="3x"/>
                    </div>
                )}
                <div className="card-body p-2">
                    <div className="fw-semibold small">{employee.name}</div>
                    <div className="text-muted small">{employee.jobTitle}</div>
                    <label htmlFor={inputId} className="btn btn-sm btn-outline-primary mt-2 w-100">
                        <FontAwesomeIcon icon={faUpload} className="me-1"/>Foto hochladen
                    </label>
                    <input id={inputId} type="file" accept="image/png,image/jpeg,image/webp"
                           className="visually-hidden" onChange={onUpload}/>
                    {status && <div className="small mt-1 text-danger" role="status">{status}</div>}
                </div>
            </div>
        </div>
    );
}
