//! Temporary diagnostic of unchanged 083e inheritance limits, not qualification.
use serde_json::{json, Value};
use std::{fs, path::PathBuf};
use yamaa_adapters::{shipped_schema, yaml_decode::decode_yaml};
use yamaa_core::schema::{
    ConstraintError, Document, InheritanceDependencyError, InheritanceReferenceError,
    NormalizationBudget, NormalizationError, NormalizationLimits, ValidationError,
};
use yamaa_engine::{
    inheritance::{self, Source, SourceError, SourcePort},
    inheritance_preparation::{self as preparation, PathPort},
};

const RUNTIME_SOURCE: &str = "083e0b35de8ec31b6eab1de7e2a6b231f04e1808";

struct Port {
    parent: Document,
    reads: usize,
}
impl SourcePort for Port {
    type Error = String;
    fn canonicalize(&mut self, _: &str, written: &str) -> Result<Source, SourceError<String>> {
        if written != "parent.yaml" {
            return Err(SourceError::Unavailable);
        }
        Ok(Source {
            identity: "parent.yaml".into(),
            display_path: "parent.yaml".into(),
        })
    }
    fn read(&mut self, _: &Source) -> Result<Document, SourceError<String>> {
        self.reads += 1;
        Ok(self.parent.clone())
    }
}
impl PathPort for Port {
    fn rebase(
        &mut self,
        _: &Source,
        _: &Source,
        written: &str,
        max: usize,
    ) -> Result<String, String> {
        if written.len() > max {
            return Err("path allowance".into());
        }
        Ok(written.into())
    }
}

fn document(width: usize, complex: bool) -> String {
    let mut names = vec!["ID".to_string()];
    names.extend((1..width).map(|i| format!("F{i:03}")));
    let mut columns = "  - {name: ID, type: str, derivation: SRC.ID}\n".to_string();
    for (index, name) in names.iter().enumerate().skip(1) {
        if complex {
            columns.push_str(&format!(
                "  - name: {name}\n    type: str\n    derivation:\n      case:\n        - {{when: \"SRC.A = 'x' AND SRC.B = '{}'\", then: {{literal: P}}}}\n        - {{when: \"SRC.A IS NULL\", then: {{literal: Q}}}}\n        - {{otherwise: SRC.A}}\n", index % 3));
        } else {
            columns.push_str(&format!(
                "  - {{name: {name}, type: str, derivation: SRC.A}}\n"
            ));
        }
    }
    format!("schema_version: '1.0'\ndomain: TEST\nkeys: [ID]\ninput: {{SRC: input.csv}}\ncolumns:\n{columns}output: {{path: output.csv, columns: [{}]}}\n", names.join(", "))
}

fn normalization_error(error: &preparation::Error<String>) -> Option<&NormalizationError> {
    match error {
        preparation::Error::Normalize(context) => Some(&context.error),
        preparation::Error::Composition(context) => Some(&context.error),
        preparation::Error::Traversal(inheritance::Error::Layer { error, .. }) => Some(error),
        preparation::Error::Dependencies(context) => match &context.error {
            InheritanceDependencyError::Normalization(error)
            | InheritanceDependencyError::Reference(InheritanceReferenceError::Normalization(
                error,
            )) => Some(error),
            _ => None,
        },
        _ => None,
    }
}
fn exhaustion(error: &preparation::Error<String>) -> Value {
    match normalization_error(error) {
        Some(NormalizationError::Limit { resource, limit }) => json!({
            "owner": "normalization", "resource": format!("{resource:?}"), "limit": limit,
            "required": null, "required_status": "not exposed by unchanged typed error"
        }),
        Some(NormalizationError::Validation(ValidationError::Constraint(
            ConstraintError::Work { limit },
        ))) => json!({
            "owner": "validation", "resource": "Work", "limit": limit,
            "required": null, "required_status": "not exposed by unchanged typed error"
        }),
        _ => json!(null),
    }
}

fn main() {
    let output = PathBuf::from(std::env::args().nth(1).expect("output directory"));
    fs::create_dir_all(&output).unwrap();
    let schema = shipped_schema::capture().expect("unchanged shipped schema admission");
    let mut records = Vec::new();
    for (width, complex) in [(40, true), (150, true), (256, true), (256, false)] {
        let body = document(width, complex);
        for inherited in [true, false] {
            let case = format!(
                "width-{width}-{}-{}",
                if complex { "complex" } else { "simple" },
                if inherited { "parent" } else { "empty-parents" }
            );
            let directory = output.join(&case);
            fs::create_dir_all(&directory).unwrap();
            let entry = if inherited {
                "schema_version: '1.0'\nparents: [parent.yaml]\n".to_string()
            } else {
                body.replace("domain: TEST", "parents: []\ndomain: TEST")
            };
            fs::write(directory.join("spec.yaml"), &entry).unwrap();
            fs::write(directory.join("parent.yaml"), &body).unwrap();
            fs::write(
                directory.join("input.csv"),
                b"ID,A,B\nS-001,x,1\nS-002,y,2\nS-003,,3\n",
            )
            .unwrap();
            let entry_document = decode_yaml(entry.as_bytes(), Default::default())
                .unwrap()
                .document;
            let parent = decode_yaml(body.as_bytes(), Default::default())
                .unwrap()
                .document;
            let mut port = Port { parent, reads: 0 };
            let limits = NormalizationLimits::default();
            let mut budget = NormalizationBudget::new(limits);
            let prepared = preparation::prepare(
                schema.structure(),
                Source {
                    identity: "spec.yaml".into(),
                    display_path: "spec.yaml".into(),
                },
                entry_document,
                &mut port,
                &mut budget,
                Default::default(),
            );
            let (nodes, text, edges) = budget.storage_used();
            let record = json!({
                "scope": "diagnostic-only", "runtime_source": RUNTIME_SOURCE,
                "case": case, "width": width, "complex": complex, "inherited": inherited,
                "parent_reads": port.reads, "accepted": prepared.is_ok(),
                "typed_error": prepared.as_ref().err().map(|e| format!("{e:?}")),
                "exhaustion": prepared.as_ref().err().map(exhaustion),
                "charged_prefix": {"work": budget.work_used(), "nodes": nodes, "text_bytes": text, "edges": edges},
                "limits": {"work": limits.validation.work, "nodes": limits.storage.nodes, "text_bytes": limits.storage.text_bytes, "edges": limits.storage.edges}
            });
            println!("{}", serde_json::to_string(&record).unwrap());
            fs::write(
                directory.join("diagnostic.json"),
                serde_json::to_vec_pretty(&record).unwrap(),
            )
            .unwrap();
            records.push(record);
        }
    }
    fs::write(
        output.join("diagnostics.json"),
        serde_json::to_vec_pretty(&records).unwrap(),
    )
    .unwrap();
}
